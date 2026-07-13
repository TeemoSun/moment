"""Authentication and user system tests."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _rsa_encrypt(public_key_pem: str, plaintext: str) -> str:
    """Simulate frontend JSEncrypt: RSA PKCS1v15 encrypt + base64."""
    pub = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    ciphertext = pub.encrypt(plaintext.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("utf-8")


def _get_public_key(client: TestClient) -> str:
    resp = client.get("/api/v1/auth/rsa-public-key")
    assert resp.status_code == 200
    return resp.json()["public_key"]


def _init_system(
    client: TestClient, email: str = "admin@test.com", nickname: str = "Admin"
) -> dict:
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post(
        "/api/v1/system/init",
        json={"email": email, "nickname": nickname, "password": enc},
    )
    assert resp.status_code == 200
    return resp.json()


def test_initialized_before_init(client: TestClient) -> None:
    resp = client.get("/api/v1/system/initialized")
    assert resp.status_code == 200
    assert resp.json()["initialized"] is False


def test_init_system(client: TestClient) -> None:
    data = _init_system(client)
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "admin"

    resp = client.get("/api/v1/system/initialized")
    assert resp.json()["initialized"] is True


def test_init_already_initialized(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post(
        "/api/v1/system/init",
        json={"email": "a2@t.com", "nickname": "Admin2", "password": enc},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "ALREADY_INITIALIZED"


def test_register_requires_invite(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "UserPass123!")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "u@t.com", "nickname": "User", "password": enc, "invite_code": "fake"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_INVITE"


def test_login_success(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "admin@test.com"
    assert "moments_token" in resp.cookies


def test_login_wrong_password(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "WrongPass123!")
    resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_login_lock_after_5_failures(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "WrongPass123!")

    for i in range(4):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
        assert resp.status_code == 401, f"attempt {i + 1}"

    resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_LOCKED"

    resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_LOCKED"


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401


def test_me_after_login(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    resp = client.get("/api/v1/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


def test_update_nickname(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")
    resp = client.patch(
        "/api/v1/me",
        json={"nickname": "NewNick"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "NewNick"


def test_change_password(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")
    old_enc = _rsa_encrypt(pub, "TestPass123!")
    new_enc = _rsa_encrypt(pub, "NewPass456!")
    resp = client.post(
        "/api/v1/me/password",
        json={"old_password": old_enc, "new_password": new_enc},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})

    new_login_enc = _rsa_encrypt(pub, "NewPass456!")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": new_login_enc},
    )
    assert resp.status_code == 200


def test_change_password_wrong_old(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")
    wrong_old = _rsa_encrypt(pub, "WrongOld123!")
    new_enc = _rsa_encrypt(pub, "NewPass456!")
    resp = client.post(
        "/api/v1/me/password",
        json={"old_password": wrong_old, "new_password": new_enc},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_csrf_required_for_logout(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_logout_with_csrf(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")
    resp = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200


def test_avatar_upload_and_access(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")

    import io

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = client.post(
        "/api/v1/me/avatar",
        files={"file": ("test.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert "/api/v1/avatars/" in resp.json()["avatar_url"]

    resp = client.get("/api/v1/avatars/default")
    assert resp.status_code == 200

    resp = client.get("/api/v1/avatars/1")
    assert resp.status_code == 200


def test_default_avatar(client: TestClient) -> None:
    resp = client.get("/api/v1/avatars/default")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_deactivate(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    csrf = client.cookies.get("moments_csrf")
    resp = client.post("/api/v1/me/deactivate", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 204

    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "ACCOUNT_DEACTIVATED"


def test_deactivated_user_cannot_login(client: TestClient, db_session: Session) -> None:
    _init_system(client)

    from app.models.users import User

    user = db_session.query(User).filter(User.email == "admin@test.com").first()
    assert user is not None
    user.status = "deactivated"
    db_session.commit()

    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    resp = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_DEACTIVATED"


def test_refresh(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "admin@test.com"


def test_weak_password_rejected(client: TestClient) -> None:
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "weak")
    resp = client.post(
        "/api/v1/system/init",
        json={"email": "a@t.com", "nickname": "Admin", "password": enc},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PASSWORD_TOO_WEAK"


def test_get_other_user(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    resp = client.get("/api/v1/users/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1
    assert resp.json()["is_deactivated"] is False


def test_get_other_user_not_found(client: TestClient) -> None:
    _init_system(client)
    pub = _get_public_key(client)
    enc = _rsa_encrypt(pub, "TestPass123!")
    client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": enc})

    resp = client.get("/api/v1/users/999")
    assert resp.status_code == 404
