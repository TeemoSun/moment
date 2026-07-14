"""好友系统测试。"""

from __future__ import annotations

import base64
from datetime import UTC, datetime

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


def _create_friendship(db_session: Session, user_a_id: int, user_b_id: int) -> None:
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


def _set_user_token(client: TestClient, user_id: int, role: str = "user") -> None:
    from app.core.jwt import create_access_token

    token = create_access_token(user_id, role)
    client.cookies.set("moments_token", token)


def test_friend_request_sent(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Friend request sent"


def test_friend_request_self(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "admin@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "CANNOT_FRIEND_SELF"


def test_friend_request_user_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "nonexistent@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"


def test_friend_request_already_friends(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _create_friendship(db_session, 1, user_b_id)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "friend@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ALREADY_FRIENDS"


def test_friend_request_duplicate(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "FRIEND_REQUEST_EXISTS"


def test_list_requests_received(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/friends/requests")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["requester"]["id"] == 1
    assert data[0]["requester"]["nickname"] == "Admin"


def test_accept_request(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/friends/requests")
    request_id = resp.json()[0]["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/friends/requests/{request_id}/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Friend request accepted"

    resp = client.get("/api/v1/friends")
    assert len(resp.json()) == 1

    _set_user_token(client, 1)
    resp = client.get("/api/v1/friends")
    assert len(resp.json()) == 1


def test_reject_request(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/friends/requests")
    request_id = resp.json()[0]["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/friends/requests/{request_id}/reject",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/friends/requests")
    assert len(resp.json()) == 0

    from app.database import SessionLocal
    from app.utils.friends import are_friends

    db = SessionLocal()
    try:
        assert not are_friends(db, 1, user_b_id)
    finally:
        db.close()


def test_list_friends(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _create_friendship(db_session, 1, user_b_id)

    resp = client.get("/api/v1/friends")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user"]["id"] == user_b_id
    assert data[0]["user"]["nickname"] == "Friend"
    assert "since" in data[0]
    assert "requester_id" in data[0]


def test_remove_friend(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _create_friendship(db_session, 1, user_b_id)

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/friends/{user_b_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/friends")
    assert len(resp.json()) == 0

    from app.database import SessionLocal
    from app.utils.friends import are_friends

    db = SessionLocal()
    try:
        assert not are_friends(db, 1, user_b_id)
    finally:
        db.close()


def test_remove_not_friend(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/friends/{user_b_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "NOT_FRIENDS"


def test_accept_request_not_recipient(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/friends/requests")
    assert len(resp.json()) == 0

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/friends/requests")
    request_id = resp.json()[0]["id"]

    _set_user_token(client, 1)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/friends/requests/{request_id}/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_accept_request_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/requests/99999/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "FRIEND_REQUEST_NOT_FOUND"


def test_friend_request_requires_csrf(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_user_in_db(db_session, "userb@test.com", "UserB")

    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_get_other_user_friendship_status(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")
    user_c_id = _create_user_in_db(db_session, "userc@test.com", "UserC")

    resp = client.get("/api/v1/users/1")
    assert resp.status_code == 200
    assert resp.json()["friendship_status"] == "self"

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "userb@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/users/2")
    assert resp.json()["friendship_status"] == "pending_sent"

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/users/1")
    assert resp.json()["friendship_status"] == "pending_received"

    resp = client.get("/api/v1/friends/requests")
    request_id = resp.json()[0]["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/friends/requests/{request_id}/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/users/1")
    assert resp.json()["friendship_status"] == "friends"

    _set_user_token(client, 1)
    resp = client.get("/api/v1/users/2")
    assert resp.json()["friendship_status"] == "friends"

    resp = client.get(f"/api/v1/users/{user_c_id}")
    assert resp.json()["friendship_status"] == "none"


def test_friend_request_to_deactivated(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_user_in_db(db_session, "deactivated@test.com", "Deactivated", status="deactivated")

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/friends/request",
        json={"email": "deactivated@test.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"
