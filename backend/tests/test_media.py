"""Media system tests."""

from __future__ import annotations

import base64
import io
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi.testclient import TestClient
from PIL import Image
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


def _make_image_bytes(size: tuple[int, int] = (100, 100), fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", size, color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_video_bytes() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=64x64:d=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                tmp_path,
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return Path(tmp_path).read_bytes()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _upload_file(client: TestClient, filename: str, content: bytes, content_type: str) -> dict:
    csrf = client.cookies.get("moments_csrf")
    buf = io.BytesIO(content)
    resp = client.post(
        "/api/v1/media/upload",
        files={"file": (filename, buf, content_type)},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_post(db_session: Session, user_id: int, visibility: str = "public") -> int:
    from app.models.posts import Post

    post = Post(user_id=user_id, content="test", visibility=visibility)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post.id


def _bind_media_to_post(db_session: Session, media_id: int, post_id: int) -> None:
    from app.models.post_media import PostMedia

    media = db_session.query(PostMedia).filter(PostMedia.id == media_id).first()
    assert media is not None
    media.post_id = post_id
    db_session.commit()


def test_upload_image(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    assert result["media_id"] >= 1
    assert result["kind"] == "image"
    assert result["status"] == "pending"


def test_upload_video(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    video_bytes = _make_video_bytes()
    result = _upload_file(client, "test.mp4", video_bytes, "video/mp4")
    assert result["media_id"] >= 1
    assert result["kind"] == "video"
    assert result["status"] == "pending"


def test_upload_too_large_image(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.config as cfg
    from app.services import media_service as ms

    monkeypatch.setattr(cfg.settings, "MEDIA_IMAGE_MAX_MB", 0)
    monkeypatch.setattr(cfg.settings, "MEDIA_VIDEO_MAX_MB", 0)
    monkeypatch.setattr(ms.settings, "MEDIA_IMAGE_MAX_MB", 0)
    monkeypatch.setattr(ms.settings, "MEDIA_VIDEO_MAX_MB", 0)
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    csrf = client.cookies.get("moments_csrf")
    buf = io.BytesIO(img_bytes)
    resp = client.post(
        "/api/v1/media/upload",
        files={"file": ("big.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


def test_upload_invalid_format(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    text_content = b"this is not an image"
    csrf = client.cookies.get("moments_csrf")
    buf = io.BytesIO(text_content)
    resp = client.post(
        "/api/v1/media/upload",
        files={"file": ("fake.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


def test_media_anonymous_requires_auth(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="public")
    _bind_media_to_post(db_session, media_id, post_id)
    client.cookies.clear()
    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_media_anonymous_requires_auth_post_missing(
    client: TestClient, db_session: Session
) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    client.cookies.clear()
    resp = client.get(f"/api/v1/posts/33/media/{media_id}/original")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_media_access_public(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="public")
    _bind_media_to_post(db_session, media_id, post_id)
    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 200


def test_media_thumb_large_access(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes(size=(800, 600))
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="public")
    _bind_media_to_post(db_session, media_id, post_id)
    for spec in ("original", "thumb", "large"):
        resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/{spec}")
        assert resp.status_code == 200, f"{spec} failed: {resp.status_code}"
        assert len(resp.content) > 0, f"{spec} empty"
    original_resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert original_resp.headers["content-type"] == "image/png"
    thumb_resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/thumb")
    assert thumb_resp.headers["content-type"] == "image/webp"
    large_resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/large")
    assert large_resp.headers["content-type"] == "image/webp"


def test_media_access_friends_forbidden(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    pub = _login(client)

    enc2 = _rsa_encrypt(pub, "User2Pass123!")
    csrf = client.cookies.get("moments_csrf")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "u2@test.com",
            "nickname": "User2",
            "password": enc2,
            "invite_code": "fake",
        },
        headers={"X-CSRF-Token": csrf} if csrf else {},
    )

    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="friends")
    _bind_media_to_post(db_session, media_id, post_id)

    from app.models.users import User

    user2 = User(
        email="viewer@test.com",
        password_hash="x",
        nickname="Viewer",
        role="user",
        status="active",
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)
    viewer_id = user2.id

    from app.core.jwt import create_access_token

    viewer_token = create_access_token(viewer_id, "user")
    client.cookies.set("moments_token", viewer_token)

    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_media_access_friends_allowed(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    from app.models.users import User

    friend = User(
        email="friend@test.com",
        password_hash="x",
        nickname="Friend",
        role="user",
        status="active",
    )
    db_session.add(friend)
    db_session.commit()
    db_session.refresh(friend)
    friend_id = friend.id

    from app.models.friendships import Friendship

    friendship = Friendship(
        user_a_id=1,
        user_b_id=friend_id,
        status="accepted",
        requester_id=1,
        created_at=datetime.now(UTC),
    )
    db_session.add(friendship)
    db_session.commit()

    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="friends")
    _bind_media_to_post(db_session, media_id, post_id)

    from app.core.jwt import create_access_token

    friend_token = create_access_token(friend_id, "user")
    client.cookies.set("moments_token", friend_token)

    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 200


def test_media_path_traversal(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="public")
    _bind_media_to_post(db_session, media_id, post_id)
    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/invalid_spec")
    assert resp.status_code == 400


def test_media_soft_deleted_post(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    post_id = _create_post(db_session, user_id=1, visibility="public")
    _bind_media_to_post(db_session, media_id, post_id)

    from app.models.posts import Post

    post = db_session.query(Post).filter(Post.id == post_id).first()
    assert post is not None
    post.deleted_at = datetime.now(UTC)
    db_session.commit()

    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 404


def test_media_not_found(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post_id = _create_post(db_session, user_id=1, visibility="public")
    resp = client.get(f"/api/v1/posts/{post_id}/media/9999/original")
    assert resp.status_code == 404


def test_media_unbound_not_accessible(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    resp = client.get(f"/api/v1/posts/9999/media/{media_id}/original")
    assert resp.status_code == 404
