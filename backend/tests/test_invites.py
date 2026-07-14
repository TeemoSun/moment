"""邀请码系统测试。"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

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


def test_create_invite(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["code"]) == 8
    assert data["status"] == "active"
    assert data["expires_at"] is not None


def test_create_permanent_invite(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] is None
    assert data["status"] == "active"


def test_create_invite_csrf_required(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_active_invite_exists(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "ACTIVE_INVITE_EXISTS"


def test_list_invites(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    code = resp.json()["code"]

    resp = client.get("/api/v1/invites")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["code"] == code


def test_revoke_invite(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    invite_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/invites/{invite_id}/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "邀请码已失效"

    resp = client.get("/api/v1/invites")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "revoked"


def test_revoke_used_invite(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    from app.models.invite_codes import InviteCode

    invite = InviteCode(
        creator_id=1,
        code="USEDTEST",
        status="used",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invite)
    db_session.commit()
    db_session.refresh(invite)
    invite_id = invite.id

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/invites/{invite_id}/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVITE_ALREADY_USED"


def test_revoke_not_found(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites/99999/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "INVITE_NOT_FOUND"


def test_renew_invite(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    old_code = resp.json()["code"]
    old_expires = resp.json()["expires_at"]

    resp = client.post(
        "/api/v1/invites/renew",
        json={"duration_days": 30},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    new_code = resp.json()["code"]
    new_expires = resp.json()["expires_at"]
    assert new_code == old_code

    resp = client.get("/api/v1/invites")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "active"
    assert data[0]["expires_at"] > old_expires
    assert new_expires == data[0]["expires_at"]


def test_renew_invite_no_active(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites/renew",
        json={"duration_days": 30},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "INVITE_NOT_FOUND"


def test_invite_disabled(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    user_id = _create_user_in_db(db_session, "normal@test.com", "Normal")
    from app.models.users import User

    user = db_session.query(User).filter(User.id == user_id).one()
    user.can_invite = False
    db_session.commit()

    _set_user_token(client, user_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/invites",
        json={"duration_days": 7},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "INVITE_DISABLED"


def test_expired_invite_lazy(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    from app.models.invite_codes import InviteCode

    invite = InviteCode(
        creator_id=1,
        code="EXPIRED1",
        status="active",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(invite)
    db_session.commit()

    resp = client.get("/api/v1/invites")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "expired"
