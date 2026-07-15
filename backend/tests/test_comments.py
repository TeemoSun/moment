"""Comment and like system tests."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.test_posts import (
    _create_friendship,
    _create_post_via_api,
    _create_user_in_db,
    _init_system,
    _login,
    _make_image_bytes,
    _set_user_token,
)


def test_create_comment_text(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Hello comment"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello comment"
    assert data["post_id"] == post_id
    assert data["like_count"] == 0
    assert data["liked_by_me"] is False
    assert data["is_owner"] is True
    assert data["can_delete"] is True
    assert data["author"]["id"] == 1


def test_create_comment_with_image(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    img_bytes = _make_image_bytes()
    buf = io.BytesIO(img_bytes)
    resp = client.post(
        "/api/v1/comments/media",
        files={"file": ("test.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    media_data = resp.json()
    media_id = media_data["media_id"]
    assert media_data["status"] == "ready"

    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Image comment", "media_id": media_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Image comment"
    assert data["image_thumb_url"] is not None
    assert data["image_large_url"] is not None

    thumb_url = data["image_thumb_url"]
    resp = client.get(thumb_url)
    assert resp.status_code == 200


def test_create_comment_empty_rejected(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "EMPTY_COMMENT"

    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "   "},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "EMPTY_COMMENT"


def test_create_comment_reply(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")
    _set_user_token(client, user_b_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "First comment"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    first_comment_id = resp.json()["id"]

    user_c_id = _create_user_in_db(db_session, "userc@test.com", "UserC")
    _set_user_token(client, user_c_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={
            "content": "Reply to first",
            "parent_comment_id": first_comment_id,
            "reply_to_user_id": user_b_id,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_comment_id"] == first_comment_id
    assert data["reply_to"] is not None
    assert data["reply_to"]["id"] == user_b_id
    assert data["reply_to"]["nickname"] == "UserB"


def test_list_comments_pagination(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    from datetime import datetime, timedelta

    from app.models.comments import Comment

    base_time = datetime(2026, 1, 1, 12, 0, 0)
    for i in range(25):
        comment = Comment(
            post_id=post_id,
            user_id=1,
            content=f"Comment {i}",
            created_at=base_time + timedelta(seconds=i),
        )
        db_session.add(comment)
    db_session.commit()

    resp = client.get(f"/api/v1/posts/{post_id}/comments?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["has_more"] is True

    resp = client.get(f"/api/v1/posts/{post_id}/comments?page=2&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 10
    assert data["page"] == 2
    assert data["has_more"] is True

    resp = client.get(f"/api/v1/posts/{post_id}/comments?page=3&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 5
    assert data["page"] == 3
    assert data["has_more"] is False


def test_comment_visibility_friends_scenario(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="friends only", visibility="friends")
    post_id = post["id"]

    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")
    _create_friendship(db_session, 1, user_b_id)

    user_c_id = _create_user_in_db(db_session, "userc@test.com", "UserC")
    _create_friendship(db_session, 1, user_c_id)

    _set_user_token(client, user_b_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Comment from B"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_b_id = resp.json()["id"]

    _set_user_token(client, user_c_id)
    resp = client.get(f"/api/v1/posts/{post_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    comment_ids = [c["id"] for c in data["items"]]
    assert comment_b_id not in comment_ids

    _set_user_token(client, 1)
    resp = client.get(f"/api/v1/posts/{post_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    comment_ids = [c["id"] for c in data["items"]]
    assert comment_b_id in comment_ids


def test_comment_visibility_viewer_friends(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="friends only", visibility="friends")
    post_id = post["id"]

    user_d_id = _create_user_in_db(db_session, "userd@test.com", "UserD")
    _create_friendship(db_session, 1, user_d_id)

    user_c_id = _create_user_in_db(db_session, "userc@test.com", "UserC")
    _create_friendship(db_session, 1, user_c_id)
    _create_friendship(db_session, user_c_id, user_d_id)

    _set_user_token(client, user_d_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Comment from D"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_d_id = resp.json()["id"]

    _set_user_token(client, user_c_id)
    resp = client.get(f"/api/v1/posts/{post_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    comment_ids = [c["id"] for c in data["items"]]
    assert comment_d_id in comment_ids

    stranger_id = _create_user_in_db(db_session, "stranger@test.com", "Stranger")
    _create_friendship(db_session, 1, stranger_id)
    _set_user_token(client, stranger_id)
    resp = client.get(f"/api/v1/posts/{post_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    comment_ids = [c["id"] for c in data["items"]]
    assert comment_d_id not in comment_ids


def test_delete_comment_by_author(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "My comment"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    resp = client.delete(
        f"/api/v1/comments/{comment_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/posts/{post_id}/comments")
    data = resp.json()
    assert all(c["id"] != comment_id for c in data["items"])


def test_delete_comment_by_post_author(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")
    _set_user_token(client, user_b_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Comment from B"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    _set_user_token(client, 1, "admin")
    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/comments/{comment_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 204


def test_delete_comment_forbidden(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    user_b_id = _create_user_in_db(db_session, "userb@test.com", "UserB")
    _set_user_token(client, user_b_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Comment from B"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    user_c_id = _create_user_in_db(db_session, "userc@test.com", "UserC")
    _set_user_token(client, user_c_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.delete(
        f"/api/v1/comments/{comment_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403


def test_like_post_toggle(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["like_count"] == 1
    assert data["liked_by_me"] is True
    assert data["target_type"] == "post"
    assert data["target_id"] == post_id

    resp = client.post(
        f"/api/v1/posts/{post_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["like_count"] == 0
    assert data["liked_by_me"] is False


def test_like_comment_toggle(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Test comment"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/comments/{comment_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["like_count"] == 1
    assert data["liked_by_me"] is True
    assert data["target_type"] == "comment"
    assert data["target_id"] == comment_id

    resp = client.post(
        f"/api/v1/comments/{comment_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["like_count"] == 0
    assert data["liked_by_me"] is False


def test_like_post_requires_view_permission(client: TestClient, db_session: Session) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="friends only", visibility="friends")
    post_id = post["id"]

    stranger_id = _create_user_in_db(db_session, "stranger@test.com", "Stranger")
    _set_user_token(client, stranger_id)
    csrf = client.cookies.get("moments_csrf")
    resp = client.post(
        f"/api/v1/posts/{post_id}/likes",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403


def test_comment_csrf_required(client: TestClient) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="test post", visibility="public")
    post_id = post["id"]

    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "No CSRF"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CSRF_FAILED"


def test_comment_image_inaccessible_after_post_invisible(
    client: TestClient, db_session: Session
) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="friends only", visibility="friends")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    img_bytes = _make_image_bytes()
    buf = io.BytesIO(img_bytes)
    resp = client.post(
        "/api/v1/comments/media",
        files={"file": ("test.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    media_id = resp.json()["media_id"]

    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Image comment", "media_id": media_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    thumb_url = resp.json()["image_thumb_url"]
    assert thumb_url is not None

    stranger_id = _create_user_in_db(db_session, "stranger@test.com", "Stranger")
    _set_user_token(client, stranger_id)
    resp = client.get(thumb_url)
    assert resp.status_code == 403


def test_comment_image_anonymous_requires_auth(
    client: TestClient, db_session: Session
) -> None:
    _init_system(client)
    _login(client)
    post = _create_post_via_api(client, content="public post", visibility="public")
    post_id = post["id"]

    csrf = client.cookies.get("moments_csrf")
    img_bytes = _make_image_bytes()
    buf = io.BytesIO(img_bytes)
    resp = client.post(
        "/api/v1/comments/media",
        files={"file": ("test.png", buf, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    media_id = resp.json()["media_id"]

    resp = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Image comment", "media_id": media_id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    thumb_url = resp.json()["image_thumb_url"]
    assert thumb_url is not None

    client.cookies.clear()
    resp = client.get(thumb_url)
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_comment_image_anonymous_requires_auth_comment_missing(
    client: TestClient,
) -> None:
    _init_system(client)
    _login(client)
    client.cookies.clear()
    resp = client.get("/api/v1/comments/9999/media/thumb")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"
