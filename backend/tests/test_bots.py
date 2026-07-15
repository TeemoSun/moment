"""AI 机器人功能测试。"""

from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _rsa_encrypt(public_key_pem: str, plaintext: str) -> str:
    pub = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    ciphertext = pub.encrypt(plaintext.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("utf-8")


def _get_public_key(client: TestClient) -> str:
    resp = client.get("/api/v1/auth/rsa-public-key")
    assert resp.status_code == 200
    return resp.json()["public_key"]


def _init_system(client: TestClient) -> None:
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post(
        "/api/v1/system/init",
        json={"email": "admin@test.com", "nickname": "Admin", "password": enc},
    )
    assert resp.status_code == 200


def _login(client: TestClient) -> str:
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    return pub


def _create_user_in_db(
    db_session: Session,
    email: str,
    nickname: str,
    role: str = "user",
    status: str = "active",
) -> int:
    from app.models.users import User

    user = User(
        email=email,
        password_hash="x",
        nickname=nickname,
        role=role,
        status=status,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


def _set_user_token(client: TestClient, user_id: int, role: str = "user") -> None:
    from app.core.jwt import create_access_token

    token = create_access_token(user_id, role)
    client.cookies.set("moments_token", token)


def _create_bot_via_api(
    client: TestClient,
    nickname: str,
    persona: str,
    **kwargs: object,
) -> dict:
    _init_system(client)
    _login(client)
    csrf = client.cookies.get("moments_csrf")
    payload: dict = {"nickname": nickname, "persona": persona, **kwargs}
    resp = client.post(
        "/api/v1/admin/bots",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_bot_in_db(
    db_session: Session,
    nickname: str,
    persona: str,
    **kwargs: object,
) -> tuple[int, int]:
    from app.models.bots import Bot
    from app.models.users import User

    user = User(
        email=f"bot_test_{nickname.lower()}@example.com",
        password_hash="x",
        nickname=nickname,
        role="bot",
        status="active",
    )
    db_session.add(user)
    db_session.flush()

    bot = Bot(
        user_id=user.id,
        persona=persona,
        poll_interval_n=kwargs.get("poll_interval_n", 600),
        poll_interval_x=kwargs.get("poll_interval_x", 60),
        lookback_days=kwargs.get("lookback_days", 3),
        comments_per_hour=kwargs.get("comments_per_hour", 10),
        max_consecutive_failures=kwargs.get("max_consecutive_failures", 5),
        llm_model=kwargs.get("llm_model"),
        enabled=kwargs.get("enabled", True),
    )
    db_session.add(bot)
    db_session.commit()
    return bot.id, user.id


def _create_post_in_db(
    db_session: Session,
    user_id: int,
    content: str,
    visibility: str = "public",
) -> int:
    from app.models.posts import Post

    post = Post(user_id=user_id, content=content, visibility=visibility)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post.id


def _create_comment_in_db(
    db_session: Session,
    post_id: int,
    user_id: int,
    content: str,
    parent_comment_id: int | None = None,
    reply_to_user_id: int | None = None,
) -> int:
    from app.models.comments import Comment

    c = Comment(
        post_id=post_id,
        user_id=user_id,
        content=content,
        parent_comment_id=parent_comment_id,
        reply_to_user_id=reply_to_user_id,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c.id


def _make_friends(db_session: Session, user_a_id: int, user_b_id: int) -> None:
    from app.models.friendships import Friendship

    lo, hi = sorted((user_a_id, user_b_id))
    f = Friendship(
        user_a_id=lo,
        user_b_id=hi,
        status="accepted",
        requester_id=lo,
        created_at=datetime.now(UTC),
        accepted_at=datetime.now(UTC),
    )
    db_session.add(f)
    db_session.commit()


def test_create_bot_via_api(client: TestClient, db_session: Session) -> None:
    data = _create_bot_via_api(client, "TestBot", "我是一个测试机器人")
    assert data["nickname"] == "TestBot"
    assert data["persona"] == "我是一个测试机器人"
    assert data["enabled"] is True

    from app.models.bots import Bot
    from app.models.users import User

    user = db_session.query(User).filter(User.id == data["user_id"]).first()
    assert user is not None
    assert user.role == "bot"
    bot = db_session.query(Bot).filter(Bot.id == data["id"]).first()
    assert bot is not None
    assert bot.persona == "我是一个测试机器人"


def test_bot_cannot_login(client: TestClient, db_session: Session) -> None:
    _create_bot_in_db(db_session, "NoLoginBot", "不能登录的机器人")

    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bot_test_nologinbot@example.com", "password": enc},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "BOT_LOGIN_FORBIDDEN"


def test_list_bots_public(client: TestClient, db_session: Session) -> None:
    _, bot_user_id_1 = _create_bot_in_db(db_session, "EnabledBot", "启用的机器人")
    _, bot_user_id_2 = _create_bot_in_db(db_session, "DisabledBot", "停用的机器人", enabled=False)

    user_id = _create_user_in_db(db_session, "user@test.com", "User")
    _set_user_token(client, user_id, "user")

    resp = client.get("/api/v1/friends/bots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["nickname"] == "EnabledBot"
    assert data[0]["is_friend"] is False


def test_add_bot_friend(client: TestClient, db_session: Session) -> None:
    _, bot_user_id = _create_bot_in_db(db_session, "FriendBot", "加好友机器人")
    _init_system(client)
    _login(client)
    user_id = _create_user_in_db(db_session, "user@test.com", "User")
    _set_user_token(client, user_id, "user")

    _make_friends(db_session, user_id, bot_user_id)

    resp = client.get("/api/v1/friends")
    assert resp.status_code == 200
    friends = resp.json()
    assert len(friends) == 1
    assert friends[0]["user"]["id"] == bot_user_id

    resp = client.get("/api/v1/friends/bots")
    assert resp.status_code == 200
    bots = resp.json()
    assert len(bots) == 1
    assert bots[0]["is_friend"] is True

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/friends/bots/{bot_user_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ALREADY_FRIENDS"


def test_remove_bot_friend(client: TestClient, db_session: Session) -> None:
    _, bot_user_id = _create_bot_in_db(db_session, "RemoveBot", "删好友机器人")
    _init_system(client)
    _login(client)
    user_id = _create_user_in_db(db_session, "user@test.com", "User")
    _make_friends(db_session, user_id, bot_user_id)
    _set_user_token(client, user_id, "user")

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/friends/{bot_user_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/friends")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_bot_replies_friend_post(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "这是一条机器人评论")
    _, bot_user_id = _create_bot_in_db(db_session, "ReplyBot", "评论机器人")
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    post_id = _create_post_in_db(db_session, user_id, "今天天气真好")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))

    from app.models.bot_reply_logs import BotReplyLog
    from app.models.comments import Comment

    db = db_session
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
    bot_comments = [c for c in comments if c.user_id == bot_user_id]
    assert len(bot_comments) == 1
    assert bot_comments[0].content == "这是一条机器人评论"

    logs = db.query(BotReplyLog).filter(BotReplyLog.bot_user_id == bot_user_id).all()
    assert len(logs) == 1
    assert logs[0].kind == "post_reply"


def test_bot_skips_non_friend_public_post(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人评论")
    _, bot_user_id = _create_bot_in_db(db_session, "SkipBot", "跳过机器人")
    user_id = _create_user_in_db(db_session, "stranger@test.com", "Stranger")
    post_id = _create_post_in_db(db_session, user_id, "公开的动态")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))

    from app.models.comments import Comment

    bot_comments = (
        db_session.query(Comment)
        .filter(Comment.post_id == post_id, Comment.user_id == bot_user_id)
        .all()
    )
    assert len(bot_comments) == 0


def test_bot_no_duplicate_reply(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人评论")
    _, bot_user_id = _create_bot_in_db(db_session, "DupBot", "幂等机器人")
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    post_id = _create_post_in_db(db_session, user_id, "测试动态")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))
    asyncio.run(run_bot(bot_user_id))

    from app.models.comments import Comment

    bot_comments = (
        db_session.query(Comment)
        .filter(Comment.post_id == post_id, Comment.user_id == bot_user_id)
        .all()
    )
    assert len(bot_comments) == 1


def test_bot_replies_to_reply(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人回复")
    _, bot_user_id = _create_bot_in_db(db_session, "Reply2Bot", "回复机器人")
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    post_id = _create_post_in_db(db_session, user_id, " original 动态")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))

    from app.models.comments import Comment

    bot_comment = (
        db_session.query(Comment)
        .filter(Comment.post_id == post_id, Comment.user_id == bot_user_id)
        .first()
    )
    assert bot_comment is not None

    _create_comment_in_db(
        db_session,
        post_id,
        user_id,
        "谢谢你的评论",
        parent_comment_id=bot_comment.id,
        reply_to_user_id=bot_user_id,
    )

    asyncio.run(run_bot(bot_user_id))

    from app.models.bot_reply_logs import BotReplyLog

    reply_logs = (
        db_session.query(BotReplyLog)
        .filter(
            BotReplyLog.bot_user_id == bot_user_id,
            BotReplyLog.kind == "comment_reply",
        )
        .all()
    )
    assert len(reply_logs) == 1

    bot_reply = (
        db_session.query(Comment)
        .filter(
            Comment.post_id == post_id,
            Comment.user_id == bot_user_id,
            Comment.reply_to_user_id == user_id,
        )
        .first()
    )
    assert bot_reply is not None
    assert bot_reply.content == "机器人回复"

    asyncio.run(run_bot(bot_user_id))
    reply_logs2 = (
        db_session.query(BotReplyLog)
        .filter(
            BotReplyLog.bot_user_id == bot_user_id,
            BotReplyLog.kind == "comment_reply",
        )
        .all()
    )
    assert len(reply_logs2) == 1


def test_bot_does_not_reply_to_bot(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人评论")
    _, bot_a_id = _create_bot_in_db(db_session, "BotA", "机器人A")
    _, bot_b_id = _create_bot_in_db(db_session, "BotB", "机器人B")
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_a_id, user_id)
    _make_friends(db_session, bot_b_id, user_id)
    post_id = _create_post_in_db(db_session, user_id, "测试动态")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_a_id))

    from app.models.comments import Comment

    bot_a_comment = (
        db_session.query(Comment)
        .filter(Comment.post_id == post_id, Comment.user_id == bot_a_id)
        .first()
    )
    assert bot_a_comment is not None

    _create_comment_in_db(
        db_session,
        post_id,
        bot_b_id,
        "BotB的评论",
        parent_comment_id=bot_a_comment.id,
        reply_to_user_id=bot_a_id,
    )

    asyncio.run(run_bot(bot_a_id))

    bot_a_replies = (
        db_session.query(Comment)
        .filter(
            Comment.post_id == post_id,
            Comment.user_id == bot_a_id,
            Comment.reply_to_user_id == bot_b_id,
        )
        .all()
    )
    assert len(bot_a_replies) == 0


def test_rate_limit(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人评论")
    _, bot_user_id = _create_bot_in_db(db_session, "RateBot", "限频机器人", comments_per_hour=2)
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    _create_post_in_db(db_session, user_id, "动态1")
    _create_post_in_db(db_session, user_id, "动态2")
    _create_post_in_db(db_session, user_id, "动态3")

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))

    from app.models.comments import Comment

    bot_comments = db_session.query(Comment).filter(Comment.user_id == bot_user_id).all()
    assert len(bot_comments) == 2


def test_auto_pause_on_failures(
    client: TestClient,
    db_session: Session,
) -> None:
    _, bot_user_id = _create_bot_in_db(
        db_session, "FailBot", "失败机器人", max_consecutive_failures=2
    )
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    _create_post_in_db(db_session, user_id, "测试动态")

    from app.models.bots import Bot
    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))
    asyncio.run(run_bot(bot_user_id))

    bot = db_session.query(Bot).filter(Bot.user_id == bot_user_id).first()
    assert bot.auto_paused is True
    assert bot.consecutive_failures == 2

    asyncio.run(run_bot(bot_user_id))
    db_session.expire_all()
    bot = db_session.query(Bot).filter(Bot.user_id == bot_user_id).first()
    assert bot.auto_paused is True
    assert bot.consecutive_failures == 2


def test_lookback_window(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MOCK_RESPONSE", "机器人评论")
    _, bot_user_id = _create_bot_in_db(db_session, "LookBot", "回看机器人", lookback_days=1)
    user_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _make_friends(db_session, bot_user_id, user_id)
    post_id = _create_post_in_db(db_session, user_id, "旧动态")

    from app.models.posts import Post

    post = db_session.query(Post).filter(Post.id == post_id).first()
    post.created_at = datetime.now(UTC) - timedelta(days=3)
    db_session.commit()

    from app.services.bot_engine import run_bot

    asyncio.run(run_bot(bot_user_id))

    from app.models.comments import Comment

    bot_comments = (
        db_session.query(Comment)
        .filter(Comment.post_id == post_id, Comment.user_id == bot_user_id)
        .all()
    )
    assert len(bot_comments) == 0


def test_admin_trigger_bot(client: TestClient, db_session: Session) -> None:
    data = _create_bot_via_api(client, "TriggerBot", "触发机器人")
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/admin/bots/{data['id']}/trigger",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_admin_update_bot(client: TestClient, db_session: Session) -> None:
    data = _create_bot_via_api(client, "UpdateBot", "原始人设")
    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/bots/{data['id']}",
        json={"persona": "新人设", "enabled": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["persona"] == "新人设"
    assert result["enabled"] is False


def test_admin_delete_bot(client: TestClient, db_session: Session) -> None:
    data = _create_bot_via_api(client, "DeleteBot", "删除机器人")
    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/admin/bots/{data['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    from app.models.bots import Bot

    bot = db_session.query(Bot).filter(Bot.id == data["id"]).first()
    assert bot.enabled is False
    assert bot.auto_paused is True


def test_get_bot_user_profile(client: TestClient, db_session: Session) -> None:
    data = _create_bot_via_api(client, "ProfileBot", "这是一个用于测试个人资料的机器人简介")
    resp = client.get(f"/api/v1/users/{data['user_id']}")
    assert resp.status_code == 200
    result = resp.json()
    assert result["is_bot"] is True
    assert result["persona_brief"] is not None
    assert len(result["persona_brief"]) > 0
