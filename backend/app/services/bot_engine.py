"""机器人轮询引擎：自动评论好友动态、回复好友对自己评论的回复。"""

from __future__ import annotations

import base64
import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_storage_root
from app.models.bot_reply_logs import BotReplyLog
from app.models.bots import Bot
from app.models.comments import Comment
from app.models.friendships import Friendship
from app.models.post_media import PostMedia
from app.models.posts import Post
from app.models.users import User
from app.services import llm_service
from app.utils.friends import are_friends
from app.utils.time import utcnow

logger = logging.getLogger("app.bot_engine")


def _get_session() -> Session:
    from app.database import SessionLocal

    return SessionLocal()


def _get_friend_ids(db: Session, bot_user_id: int) -> set[int]:
    rows = (
        db.query(Friendship)
        .filter(
            Friendship.status == "accepted",
            (Friendship.user_a_id == bot_user_id) | (Friendship.user_b_id == bot_user_id),
        )
        .all()
    )
    ids: set[int] = set()
    for f in rows:
        ids.add(f.user_b_id if f.user_a_id == bot_user_id else f.user_a_id)
    return ids


def _count_recent_comments(db: Session, bot_user_id: int) -> int:
    cutoff = utcnow() - timedelta(hours=1)
    return (
        db.query(func.count(Comment.id))
        .filter(
            Comment.user_id == bot_user_id,
            Comment.created_at >= cutoff,
            Comment.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )


def _already_replied_post(db: Session, bot_user_id: int, post_id: int) -> bool:
    return (
        db.query(BotReplyLog)
        .filter(
            BotReplyLog.bot_user_id == bot_user_id,
            BotReplyLog.post_id == post_id,
            BotReplyLog.kind == "post_reply",
        )
        .first()
        is not None
    )


def _already_replied_comment(db: Session, bot_user_id: int, target_comment_id: int) -> bool:
    return (
        db.query(BotReplyLog)
        .filter(
            BotReplyLog.bot_user_id == bot_user_id,
            BotReplyLog.kind == "comment_reply",
            BotReplyLog.target_comment_id == target_comment_id,
        )
        .first()
        is not None
    )


def _media_placeholder_for_post(db: Session, post_id: int) -> str:
    """返回该动态媒体占位文本，如「[图片][图片]」或「[视频]」；无媒体返回空串。"""
    rows = (
        db.query(PostMedia)
        .filter(PostMedia.post_id == post_id)
        .order_by(PostMedia.sort_order)
        .all()
    )
    parts: list[str] = []
    for m in rows:
        if m.kind == "image":
            parts.append("[图片]")
        elif m.kind == "video":
            parts.append("[视频]")
    return "".join(parts)


def _format_post_for_context(db: Session, post: Post, now: datetime) -> str:
    """把一条动态及其评论格式化为上下文文本片段。"""
    media_tag = _media_placeholder_for_post(db, post.id)
    ts = post.created_at.strftime("%Y-%m-%d %H:%M")
    body = post.content or ""
    if media_tag:
        body = f"{body} {media_tag}" if body else media_tag
    lines = [f"[{ts}] {body}".rstrip()]
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post.id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at)
        .all()
    )
    for c in comments:
        c_author = db.query(User).filter(User.id == c.user_id).first()
        c_name = c_author.nickname if c_author else "未知"
        c_ts = c.created_at.strftime("%Y-%m-%d %H:%M")
        c_body = c.content or ""
        if c.image_thumb_path:
            c_body = f"{c_body} [图片]".strip()
        lines.append(f"  └ {c_name}({c_ts})：{c_body}")
    return "\n".join(lines)


def _build_author_context(
    db: Session, author_id: int, exclude_post_id: int | None = None
) -> str | None:
    """构建作者最近 10 条朋友圈（含评论）的上下文文本。无则返回 None。"""
    now = utcnow()
    q = (
        db.query(Post)
        .filter(Post.user_id == author_id, Post.deleted_at.is_(None))
        .order_by(Post.created_at.desc())
    )
    if exclude_post_id is not None:
        q = q.filter(Post.id != exclude_post_id)
    posts = q.limit(10).all()
    if not posts:
        return None
    now_str = now.strftime("%Y-%m-%d %H:%M")
    header = f"当前时间：{now_str}\n以下是作者最近的朋友圈动态："
    body = "\n\n".join(_format_post_for_context(db, p, now) for p in posts)
    return f"{header}\n\n{body}"


def _get_post_images_b64(db: Session, post_id: int) -> list[str]:
    media_rows = (
        db.query(PostMedia)
        .filter(
            PostMedia.post_id == post_id,
            PostMedia.kind == "image",
            PostMedia.large_path.isnot(None),
        )
        .order_by(PostMedia.sort_order)
        .all()
    )
    storage_root = get_storage_root()
    result: list[str] = []
    for m in media_rows:
        if not m.large_path:
            continue
        p = (storage_root / m.large_path).resolve()
        if p.is_file():
            result.append(base64.b64encode(p.read_bytes()).decode())
    return result


def _get_comment_image_b64(db: Session, comment: Comment) -> list[str]:
    """读取评论附带图片（large 版）的 base64，无图返回空列表。"""
    if not comment.image_large_path:
        return []
    p = (get_storage_root() / comment.image_large_path).resolve()
    if not p.is_file():
        return []
    return [base64.b64encode(p.read_bytes()).decode()]


async def run_bot(bot_user_id: int) -> None:
    db = _get_session()
    try:
        bot = db.query(Bot).filter(Bot.user_id == bot_user_id).first()
        if not bot or not bot.enabled or bot.auto_paused:
            return
        user = db.query(User).filter(User.id == bot_user_id).first()
        if not user or user.status != "active" or user.role != "bot":
            return
        try:
            await _run_bot_inner(db, bot, user)
            bot.consecutive_failures = 0
        except Exception:
            logger.exception("bot %s run failed", bot_user_id)
            bot.consecutive_failures += 1
            if bot.consecutive_failures >= bot.max_consecutive_failures:
                bot.auto_paused = True
                logger.warning(
                    "bot %s auto-paused after %d failures",
                    bot_user_id,
                    bot.consecutive_failures,
                )
        bot.last_run_at = utcnow()
        n = bot.poll_interval_n
        x = bot.poll_interval_x
        bot.next_run_at = utcnow() + timedelta(seconds=random.randint(max(1, n - x), n + x))
        db.commit()
    finally:
        db.close()


async def _run_bot_inner(db: Session, bot: Bot, user: User) -> None:
    from app.services.llm_service import _load_llm_config

    llm_cfg = _load_llm_config()
    friend_ids = _get_friend_ids(db, user.id)
    if not friend_ids:
        return
    rate_used = _count_recent_comments(db, user.id)
    rate_limit = bot.comments_per_hour

    cutoff = utcnow() - timedelta(days=bot.lookback_days)
    posts = (
        db.query(Post)
        .filter(
            Post.deleted_at.is_(None),
            Post.user_id.in_(friend_ids),
            Post.created_at >= cutoff,
        )
        .order_by(Post.created_at.desc())
        .limit(50)
        .all()
    )

    for post in posts:
        if rate_used >= rate_limit:
            break
        if _already_replied_post(db, user.id, post.id):
            continue
        author = db.query(User).filter(User.id == post.user_id).first()
        if not author:
            continue
        images_b64 = _get_post_images_b64(db, post.id)
        author_context = _build_author_context(db, author.id, exclude_post_id=post.id)
        content = await llm_service.generate_comment(
            persona=bot.persona,
            post_content=post.content,
            author_name=author.nickname,
            images_b64=images_b64 or None,
            model=bot.llm_model,
            cfg=llm_cfg,
            author_context=author_context,
        )
        if not content:
            continue
        comment = Comment(
            post_id=post.id,
            user_id=user.id,
            parent_comment_id=None,
            reply_to_user_id=None,
            content=content,
        )
        db.add(comment)
        db.flush()
        db.add(
            BotReplyLog(
                bot_user_id=user.id,
                post_id=post.id,
                kind="post_reply",
                target_comment_id=None,
                reply_comment_id=comment.id,
            )
        )
        db.commit()
        rate_used += 1

    bot_commented_post_ids = (
        db.query(BotReplyLog.post_id).filter(BotReplyLog.bot_user_id == user.id).distinct().all()
    )
    post_ids = [r[0] for r in bot_commented_post_ids]
    if not post_ids:
        return

    for pid in post_ids:
        if rate_used >= rate_limit:
            break
        targets = (
            db.query(Comment)
            .filter(
                Comment.post_id == pid,
                Comment.reply_to_user_id == user.id,
                Comment.deleted_at.is_(None),
                Comment.user_id != user.id,
            )
            .all()
        )
        for tc in targets:
            if rate_used >= rate_limit:
                break
            if _already_replied_comment(db, user.id, tc.id):
                continue
            tc_author = db.query(User).filter(User.id == tc.user_id).first()
            if not tc_author or tc_author.role == "bot":
                continue
            if not are_friends(db, user.id, tc.user_id):
                continue
            inner_post = db.query(Post).filter(Post.id == pid, Post.deleted_at.is_(None)).first()
            if not inner_post:
                continue
            post_author = db.query(User).filter(User.id == inner_post.user_id).first()
            author_name = post_author.nickname if post_author else "未知"
            author_context = _build_author_context(
                db, inner_post.user_id, exclude_post_id=inner_post.id
            )
            reply_content = await llm_service.generate_reply(
                persona=bot.persona,
                post_content=inner_post.content,
                author_name=author_name,
                reply_to_name=tc_author.nickname,
                reply_to_content=tc.content or "",
                model=bot.llm_model,
                cfg=llm_cfg,
                author_context=author_context,
                images_b64=_get_comment_image_b64(db, tc) or None,
            )
            if not reply_content:
                continue
            comment = Comment(
                post_id=pid,
                user_id=user.id,
                parent_comment_id=tc.id,
                reply_to_user_id=tc.user_id,
                content=reply_content,
            )
            db.add(comment)
            db.flush()
            db.add(
                BotReplyLog(
                    bot_user_id=user.id,
                    post_id=pid,
                    kind="comment_reply",
                    target_comment_id=tc.id,
                    reply_comment_id=comment.id,
                )
            )
            db.commit()
            rate_used += 1
