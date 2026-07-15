"""Post system tests."""

from __future__ import annotations

import base64
import io
from datetime import UTC, datetime

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


def _create_post_via_api(
    client: TestClient,
    content: str = "Hello",
    visibility: str = "public",
    media_ids: list[int] | None = None,
) -> dict:
    csrf = client.cookies.get("moments_csrf")
    payload: dict = {"content": content, "visibility": visibility}
    if media_ids:
        payload["media_ids"] = media_ids
    resp = client.post(
        "/api/v1/posts",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    return resp.json()


def _create_user_in_db(db_session: Session, email: str, nickname: str, role: str = "user") -> int:
    from app.models.users import User

    user = User(
        email=email,
        password_hash="x",
        nickname=nickname,
        role=role,
        status="active",
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
    )
    db_session.add(f)
    db_session.commit()


def _set_user_token(client: TestClient, user_id: int, role: str = "user") -> None:
    from app.core.jwt import create_access_token

    token = create_access_token(user_id, role)
    client.cookies.set("moments_token", token)


def test_create_post_text_only(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    data = _create_post_via_api(client, content="Hello world", visibility="public")
    assert data["content"] == "Hello world"
    assert data["visibility"] == "public"
    assert data["like_count"] == 0
    assert data["comment_count"] == 0
    assert data["liked_by_me"] is False
    assert data["is_owner"] is True
    assert data["author"]["id"] == 1
    assert data["media"] == []


def test_create_post_with_media(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    data = _create_post_via_api(client, content="With media", media_ids=[media_id])
    assert len(data["media"]) == 1
    assert data["media"][0]["kind"] == "image"
    assert data["media"][0]["original_url"] is not None
    assert data["media"][0]["id"] == media_id


def test_create_post_media_not_owned(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]

    from app.models.post_media import PostMedia

    media = db_session.query(PostMedia).filter(PostMedia.id == media_id).first()
    assert media is not None
    other_user_id = _create_user_in_db(db_session, "other@test.com", "Other")
    media.owner_id = other_user_id
    db_session.commit()

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/posts",
        json={"content": "test", "media_ids": [media_id]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "MEDIA_NOT_OWNED"


def test_create_post_media_already_used(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]

    _create_post_via_api(client, content="first", media_ids=[media_id])

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/posts",
        json={"content": "second", "media_ids": [media_id]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MEDIA_ALREADY_USED"


def test_feed_visibility_public(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_post_via_api(client, content="public post", visibility="public")

    viewer_id = _create_user_in_db(db_session, "viewer@test.com", "Viewer")
    _set_user_token(client, viewer_id)

    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content"] == "public post"


def test_feed_visibility_friends(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_post_via_api(client, content="friends only", visibility="friends")

    friend_id = _create_user_in_db(db_session, "friend@test.com", "Friend")
    _create_friendship(db_session, 1, friend_id)

    _set_user_token(client, friend_id)
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    stranger_id = _create_user_in_db(db_session, "stranger@test.com", "Stranger")
    _set_user_token(client, stranger_id)
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0


def test_feed_self_posts_visible(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    _create_post_via_api(client, content="my friends post", visibility="friends")

    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_feed_cursor_pagination(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)

    from datetime import datetime, timedelta

    from app.models.posts import Post

    base_time = datetime(2026, 1, 1, 12, 0, 0)
    for i in range(25):
        post = Post(
            user_id=1,
            content=f"post {i}",
            visibility="public",
            created_at=base_time + timedelta(seconds=i),
            updated_at=base_time + timedelta(seconds=i),
        )
        db_session.add(post)
    db_session.commit()

    all_ids: list[int] = []
    cursor: str | None = None
    page_count = 0
    while True:
        url = "/api/v1/feed?limit=10"
        if cursor:
            url += f"&cursor={cursor}"
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        page_count += 1
        for item in data["items"]:
            assert item["id"] not in all_ids
            all_ids.append(item["id"])
        if data["has_more"]:
            assert data["next_cursor"] is not None
            cursor = data["next_cursor"]
        else:
            assert data["next_cursor"] is None
            break

    assert len(all_ids) == 25
    assert page_count == 3


def test_get_post_detail(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    created = _create_post_via_api(client, content="detail test", visibility="public")
    post_id = created["id"]

    resp = client.get(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "detail test"
    assert data["id"] == post_id

    resp = client.get("/api/v1/posts/99999")
    assert resp.status_code == 404

    _create_post_via_api(client, content="friends detail", visibility="friends")
    friend_post_id = None
    resp = client.get("/api/v1/feed")
    for item in resp.json()["items"]:
        if item["content"] == "friends detail":
            friend_post_id = item["id"]
            break
    assert friend_post_id is not None

    stranger_id = _create_user_in_db(db_session, "stranger2@test.com", "Stranger2")
    _set_user_token(client, stranger_id)
    resp = client.get(f"/api/v1/posts/{friend_post_id}")
    assert resp.status_code == 403


def test_delete_post_by_author(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    created = _create_post_via_api(client, content="to delete")
    post_id = created["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/feed")
    assert all(item["id"] != post_id for item in resp.json()["items"])

    resp = client.get(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 404


def test_delete_post_by_admin(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_post_via_api(client, content="admin delete me")

    user_id = _create_user_in_db(db_session, "user@test.com", "User")
    _set_user_token(client, user_id)
    resp = client.get("/api/v1/feed")
    post_id = resp.json()["items"][0]["id"]

    _set_user_token(client, 1, "admin")
    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204


def test_delete_post_forbidden(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    created = _create_post_via_api(client, content="not yours")
    post_id = created["id"]

    other_id = _create_user_in_db(db_session, "other2@test.com", "Other2")
    _set_user_token(client, other_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403


def test_delete_already_deleted(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    created = _create_post_via_api(client, content="delete twice")
    post_id = created["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404


def test_user_posts(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    _create_post_via_api(client, content="public from admin", visibility="public")
    _create_post_via_api(client, content="friends from admin", visibility="friends")

    viewer_id = _create_user_in_db(db_session, "viewer2@test.com", "Viewer2")
    _set_user_token(client, viewer_id)
    resp = client.get("/api/v1/users/1/posts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content"] == "public from admin"

    _set_user_token(client, 1)
    resp = client.get("/api/v1/users/1/posts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2


def test_xss_content(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    xss = "<script>alert(1)</script>"
    _create_post_via_api(client, content=xss, visibility="public")

    resp = client.get("/api/v1/feed")
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["content"] == xss


def test_invalid_cursor(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    resp = client.get("/api/v1/feed?cursor=xxx")
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_CURSOR"

    bad = base64.urlsafe_b64encode(b"2026-01-01 00:00:00|abc").decode()
    resp = client.get(f"/api/v1/feed?cursor={bad}")
    assert resp.status_code == 400


def test_create_post_requires_csrf(client: TestClient) -> None:
    _init_system(client)
    _login(client)

    resp = client.post(
        "/api/v1/posts",
        json={"content": "no csrf"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_feed_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 401


def test_create_post_duplicate_media_ids(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        "/api/v1/posts",
        json={"content": "dup media", "media_ids": [media_id, media_id]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_media_inaccessible_after_post_deleted(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    img_bytes = _make_image_bytes()
    result = _upload_file(client, "test.png", img_bytes, "image/png")
    media_id = result["media_id"]
    created = _create_post_via_api(client, content="with media to delete", media_ids=[media_id])
    post_id = created["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/posts/{post_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/posts/{post_id}/media/{media_id}/original")
    assert resp.status_code == 404


def test_feed_like_authors_visibility_friends(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="friends only", visibility="friends")
    post_id = post["id"]

    user_b_id = _create_user_in_db(db_session, "b@test.com", "UserB")
    user_c_id = _create_user_in_db(db_session, "c@test.com", "UserC")
    _create_friendship(db_session, 1, user_b_id)
    _create_friendship(db_session, 1, user_c_id)

    csrf = client.cookies.get("moments_csrf")
    for uid in (user_b_id, user_c_id):
        _set_user_token(client, uid)
        resp = client.post(
            f"/api/v1/posts/{post_id}/likes",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200

    _set_user_token(client, user_b_id)
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    author_ids = {a["id"] for a in item["like_authors"]}
    assert user_b_id in author_ids
    assert user_c_id not in author_ids

    _set_user_token(client, user_c_id)
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    author_ids = {a["id"] for a in item["like_authors"]}
    assert user_c_id in author_ids
    assert user_b_id not in author_ids


def test_feed_like_authors_public(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="public", visibility="public")
    post_id = post["id"]

    liker_id = _create_user_in_db(db_session, "liker@test.com", "Liker")
    csrf = client.cookies.get("moments_csrf")
    _set_user_token(client, liker_id)
    resp = client.post(
        f"/api/v1/posts/{post_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    _set_user_token(client, liker_id)
    resp = client.get("/api/v1/feed")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["like_authors"][0]["nickname"] == "Liker"
    assert item["like_authors"][0]["id"] == liker_id
