"""V1 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, comments, friends, media, posts, system, users

router = APIRouter()
router.include_router(system.router, prefix="/system", tags=["system"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(posts.router, tags=["posts"])
router.include_router(users.router, tags=["users"])
router.include_router(media.router, tags=["media"])
router.include_router(comments.router, tags=["comments"])
router.include_router(friends.router, prefix="/friends", tags=["friends"])
