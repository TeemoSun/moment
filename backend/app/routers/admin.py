from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_admin_user
from app.models import InviteCode, User
from app.schemas import InviteCodeOut, Paginated, UserBrief

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/invite-codes", response_model=InviteCodeOut, status_code=201)
async def create_invite_code(
    max_uses: int = Query(1, ge=1, le=100),
    expires_days: int | None = Query(None, ge=1, le=365),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    code = InviteCode(
        code=secrets.token_urlsafe(12)[:20],
        created_by=admin.id,
        max_uses=max_uses,
        expires_at=(
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=expires_days)
            if expires_days else None
        ),
    )
    db.add(code)
    await db.flush()
    return InviteCodeOut.model_validate(code)


@router.get("/invite-codes", response_model=list[InviteCodeOut])
async def list_invite_codes(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(InviteCode).order_by(InviteCode.created_at.desc()))
    return [InviteCodeOut.model_validate(c) for c in result.scalars().all()]


@router.get("/users", response_model=Paginated[UserBrief])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    items = [
        UserBrief(
            id=u.id, username=u.username, display_name=u.display_name,
            avatar_url=f"/api/media/avatar/{u.id}?v={u.avatar_media_id}" if u.avatar_media_id else None,
        )
        for u in users
    ]
    return Paginated(
        items=items, total=len(items), page=page, page_size=page_size, has_more=False
    )