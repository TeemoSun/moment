"""管理后台测试。"""

from __future__ import annotations

import base64

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
    can_invite: bool = True,
) -> int:
    from app.models.users import User

    user = User(
        email=email,
        password_hash="x",
        nickname=nickname,
        role=role,
        status=status,
        can_invite=can_invite,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


def _set_user_token(client: TestClient, user_id: int, role: str = "user") -> None:
    from app.core.jwt import create_access_token

    token = create_access_token(user_id, role)
    client.cookies.set("moments_token", token)


def _create_post_in_db(
    db_session: Session,
    user_id: int,
    content: str = "test post",
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
    content: str = "test comment",
) -> int:
    from app.models.comments import Comment

    comment = Comment(post_id=post_id, user_id=user_id, content=content)
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment.id


def _create_invite_in_db(
    db_session: Session,
    creator_id: int,
    code: str,
    status: str = "active",
) -> int:
    from app.models.invite_codes import InviteCode

    invite = InviteCode(creator_id=creator_id, code=code, status=status)
    db_session.add(invite)
    db_session.commit()
    db_session.refresh(invite)
    return invite.id


def test_admin_stats(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    u1 = _create_user_in_db(db_session, "u1@test.com", "U1")
    u2 = _create_user_in_db(db_session, "u2@test.com", "U2")
    _create_post_in_db(db_session, 1, "admin post")
    _create_post_in_db(db_session, u1, "u1 post")
    _create_post_in_db(db_session, u2, "u2 post")
    _create_invite_in_db(db_session, 1, "CODE0001", "used")
    _create_invite_in_db(db_session, 1, "CODE0002", "active")

    resp = client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_count"] == 3
    assert data["post_count"] == 3
    assert data["invite_count"] == 2
    assert data["used_invite_count"] == 1


def test_list_users_search(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    _create_user_in_db(db_session, "alice@test.com", "Alice")
    _create_user_in_db(db_session, "bob@test.com", "Bob")

    resp = client.get("/api/v1/admin/users?search=alice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "alice@test.com"


def test_list_users_pagination(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    for i in range(5):
        _create_user_in_db(db_session, f"user{i}@test.com", f"User{i}")

    resp = client.get("/api/v1/admin/users?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 6
    assert data["has_more"] is True

    resp = client.get("/api/v1/admin/users?page=3&page_size=2")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["has_more"] is False


def test_disable_user(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "target@test.com", "Target")

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"status": "disabled"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    _set_user_token(client, user_id)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_DISABLED"


def test_enable_user(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "target@test.com", "Target", status="disabled")

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"status": "active"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_restore_deactivated(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "deact@test.com", "Deact", status="deactivated")

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"restore": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_cannot_set_deactivated_via_admin(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "deact@test.com", "Deact", status="deactivated")

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"status": "active"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"

    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"status": "deactivated"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_toggle_can_invite(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "target@test.com", "Target")

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"can_invite": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["can_invite"] is False

    _set_user_token(client, user_id)
    csrf2 = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf2},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "INVITE_DISABLED"


def test_list_posts_filter(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    u_a = _create_user_in_db(db_session, "a@test.com", "A")
    u_b = _create_user_in_db(db_session, "b@test.com", "B")
    _create_post_in_db(db_session, u_a, "post a")
    _create_post_in_db(db_session, u_b, "post b")

    resp = client.get(f"/api/v1/admin/posts?user_id={u_a}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["content"] == "post a"


def test_admin_delete_post(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    post_id = _create_post_in_db(db_session, 1, "to delete")

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/admin/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/admin/posts")
    data = resp.json()
    found = [p for p in data["items"] if p["id"] == post_id]
    assert len(found) == 1
    assert found[0]["deleted"] is True


def test_list_comments(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    post_id = _create_post_in_db(db_session, 1, "post")
    _create_comment_in_db(db_session, post_id, 1, "comment1")

    resp = client.get("/api/v1/admin/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["content"] == "comment1"


def test_admin_delete_comment(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    post_id = _create_post_in_db(db_session, 1, "post")
    comment_id = _create_comment_in_db(db_session, post_id, 1, "to delete")

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/admin/comments/{comment_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/admin/comments")
    data = resp.json()
    found = [c for c in data["items"] if c["id"] == comment_id]
    assert len(found) == 1
    assert found[0]["deleted"] is True


def test_list_invites(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    _create_invite_in_db(db_session, 1, "CODE0001")
    _create_invite_in_db(db_session, 1, "CODE0002", "used")

    resp = client.get("/api/v1/admin/invites")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    codes = {i["code"] for i in data["items"]}
    assert codes == {"CODE0001", "CODE0002"}


def test_non_admin_forbidden(client: TestClient, db_session: Session) -> None:
    _init_system(client)

    user_id = _create_user_in_db(db_session, "normal@test.com", "Normal")
    _set_user_token(client, user_id)

    resp = client.get("/api/v1/admin/stats")
    assert resp.status_code == 403
    assert resp.json()["code"] == "ADMIN_REQUIRED"


def test_admin_csrf_required(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "target@test.com", "Target")

    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"status": "disabled"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"

    post_id = _create_post_in_db(db_session, 1, "post")
    resp = client.delete(f"/api/v1/admin/posts/{post_id}")
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_update_user_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        "/api/v1/admin/users/99999",
        json={"status": "disabled"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"


def test_delete_post_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        "/api/v1/admin/posts/99999",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_admin_revoke_invite(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    invite_id = _create_invite_in_db(db_session, 1, "CODE0001", "active")

    resp = client.post(
        f"/api/v1/admin/invites/{invite_id}/revoke",
        headers={"X-CSRF-Token": client.cookies.get("moments_csrf")},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "邀请码已失效"

    resp = client.get("/api/v1/admin/invites")
    statuses = {i["code"]: i["status"] for i in resp.json()["items"]}
    assert statuses["CODE0001"] == "revoked"


def test_admin_revoke_invite_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    resp = client.post(
        "/api/v1/admin/invites/99999/revoke",
        headers={"X-CSRF-Token": client.cookies.get("moments_csrf")},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "INVITE_NOT_FOUND"


def test_admin_revoke_invite_used(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    invite_id = _create_invite_in_db(db_session, 1, "CODE0001", "used")

    resp = client.post(
        f"/api/v1/admin/invites/{invite_id}/revoke",
        headers={"X-CSRF-Token": client.cookies.get("moments_csrf")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVITE_ALREADY_USED"


def test_admin_revoke_invite_csrf_required(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    invite_id = _create_invite_in_db(db_session, 1, "CODE0001", "active")

    resp = client.post(f"/api/v1/admin/invites/{invite_id}/revoke")
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"
