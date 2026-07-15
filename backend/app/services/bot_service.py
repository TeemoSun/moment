"""机器人管理服务。"""

from __future__ import annotations

import secrets

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.bots import Bot
from app.models.friendships import Friendship
from app.models.users import User
from app.schemas.bot import BotAdminOut, BotPublicOut
from app.schemas.common import AppError, ErrorCode
from app.services.user_service import avatar_url_for, upload_avatar
from app.utils.friends import are_friends
from app.utils.time import utcnow


def _bot_to_admin_out(db: Session, bot: Bot) -> dict:
    user = db.query(User).filter(User.id == bot.user_id).first()
    return BotAdminOut(
        id=bot.id,
        user_id=bot.user_id,
        nickname=user.nickname if user else "",
        email=user.email if user else "",
        avatar_url=avatar_url_for(user) if user else "/api/v1/avatars/default",
        persona=bot.persona,
        poll_interval_n=bot.poll_interval_n,
        poll_interval_x=bot.poll_interval_x,
        lookback_days=bot.lookback_days,
        comments_per_hour=bot.comments_per_hour,
        max_consecutive_failures=bot.max_consecutive_failures,
        llm_model=bot.llm_model,
        enabled=bot.enabled,
        auto_paused=bot.auto_paused,
        consecutive_failures=bot.consecutive_failures,
        last_run_at=bot.last_run_at,
        next_run_at=bot.next_run_at,
        created_at=bot.created_at,
    ).model_dump(mode="json")


def _bot_to_admin_out_with_user(db: Session, bot: Bot, user: User | None) -> dict:
    return BotAdminOut(
        id=bot.id,
        user_id=bot.user_id,
        nickname=user.nickname if user else "",
        email=user.email if user else "",
        avatar_url=avatar_url_for(user) if user else "/api/v1/avatars/default",
        persona=bot.persona,
        poll_interval_n=bot.poll_interval_n,
        poll_interval_x=bot.poll_interval_x,
        lookback_days=bot.lookback_days,
        comments_per_hour=bot.comments_per_hour,
        max_consecutive_failures=bot.max_consecutive_failures,
        llm_model=bot.llm_model,
        enabled=bot.enabled,
        auto_paused=bot.auto_paused,
        consecutive_failures=bot.consecutive_failures,
        last_run_at=bot.last_run_at,
        next_run_at=bot.next_run_at,
        created_at=bot.created_at,
    ).model_dump(mode="json")


def _bot_to_public_out(db: Session, bot: Bot, is_friend: bool) -> dict:
    user = db.query(User).filter(User.id == bot.user_id).first()
    return BotPublicOut(
        id=bot.id,
        user_id=bot.user_id,
        nickname=user.nickname if user else "",
        avatar_url=avatar_url_for(user) if user else "/api/v1/avatars/default",
        persona_brief=bot.persona[:80],
        is_friend=is_friend,
    ).model_dump(mode="json")


def create_bot(db: Session, data: dict) -> dict:
    placeholder_email = f"bot_{secrets.token_hex(8)}@bot.local"
    password_hash = hash_password(secrets.token_urlsafe(32))
    user = User(
        email=placeholder_email,
        password_hash=password_hash,
        nickname=data["nickname"],
        role="bot",
        status="active",
    )
    db.add(user)
    db.flush()
    user.email = f"bot_{user.id}@bot.local"
    db.flush()

    bot = Bot(
        user_id=user.id,
        persona=data["persona"],
        poll_interval_n=data.get("poll_interval_n", 600),
        poll_interval_x=data.get("poll_interval_x", 60),
        lookback_days=data.get("lookback_days", 3),
        comments_per_hour=data.get("comments_per_hour", 10),
        max_consecutive_failures=data.get("max_consecutive_failures", 5),
        llm_model=data.get("llm_model"),
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _bot_to_admin_out(db, bot)


def update_bot(db: Session, bot_id: int, data: dict) -> dict:
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人不存在", 404)

    user = db.query(User).filter(User.id == bot.user_id).first()

    if data.get("restore"):
        bot.auto_paused = False
        bot.consecutive_failures = 0

    if "nickname" in data and data["nickname"] is not None and user:
        user.nickname = data["nickname"]

    for field in [
        "persona",
        "poll_interval_n",
        "poll_interval_x",
        "lookback_days",
        "comments_per_hour",
        "max_consecutive_failures",
        "llm_model",
        "enabled",
    ]:
        if field in data and data[field] is not None:
            setattr(bot, field, data[field])

    db.commit()
    db.refresh(bot)
    return _bot_to_admin_out(db, bot)


def delete_bot(db: Session, bot_id: int) -> dict:
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人不存在", 404)
    bot.enabled = False
    bot.auto_paused = True
    db.commit()
    return {"message": "机器人已停用"}


def list_bots_admin(db: Session) -> list[dict]:
    bots = db.query(Bot).all()
    user_ids = [b.user_id for b in bots]
    users = (
        {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    )
    return [_bot_to_admin_out_with_user(db, b, users.get(b.user_id)) for b in bots]


def get_bot_admin(db: Session, bot_id: int) -> dict:
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人不存在", 404)
    return _bot_to_admin_out(db, bot)


def upload_bot_avatar(db: Session, bot_id: int, file: UploadFile) -> dict:
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人不存在", 404)
    user = db.query(User).filter(User.id == bot.user_id).first()
    if not user:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人用户不存在", 404)
    upload_avatar(db, user, file)
    return {"message": "头像已更新"}


def list_bots_public(db: Session, user: User) -> list[dict]:
    bots = db.query(Bot).filter(Bot.enabled.is_(True)).all()
    result: list[dict] = []
    for bot in bots:
        is_friend = are_friends(db, user.id, bot.user_id)
        result.append(_bot_to_public_out(db, bot, is_friend))
    return result


def add_bot_friend(db: Session, user: User, bot_user_id: int) -> dict:
    bot_user = db.query(User).filter(User.id == bot_user_id).first()
    if not bot_user:
        raise AppError(ErrorCode.USER_NOT_FOUND, "用户不存在", 404)
    if bot_user.role != "bot":
        raise AppError(ErrorCode.USER_NOT_FOUND, "该用户不是机器人", 404)
    if bot_user.status != "active":
        raise AppError(ErrorCode.USER_NOT_FOUND, "机器人不可用", 404)
    if are_friends(db, user.id, bot_user_id):
        raise AppError(ErrorCode.ALREADY_FRIENDS, "你们已经是好友了", 400)

    lo, hi = sorted((user.id, bot_user_id))
    f = Friendship(
        user_a_id=lo,
        user_b_id=hi,
        status="accepted",
        requester_id=user.id,
        accepted_at=utcnow(),
    )
    db.add(f)
    db.commit()
    return {"message": "已添加机器人为好友"}


def trigger_bot(db: Session, bot_id: int) -> dict:
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise AppError(ErrorCode.BOT_NOT_FOUND, "机器人不存在", 404)
    from app.scheduler import trigger_bot_now

    trigger_bot_now(bot.user_id)
    return {"message": "已触发轮询"}
