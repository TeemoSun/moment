"""V1 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    bots_admin,
    comments,
    friends,
    invites,
    media,
    posts,
    system,
    users,
)

router = APIRouter()
router.include_router(system.router, prefix="/system", tags=["system"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(posts.router, tags=["posts"])
router.include_router(users.router, tags=["users"])
router.include_router(media.router, tags=["media"])
router.include_router(comments.router, tags=["comments"])
router.include_router(friends.router, prefix="/friends", tags=["friends"])
router.include_router(invites.router, prefix="/invites", tags=["invites"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(bots_admin.router, prefix="/admin/bots", tags=["admin-bots"])
