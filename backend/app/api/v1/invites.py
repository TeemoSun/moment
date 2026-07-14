"""邀请码路由:创建、列表、失效、续期。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.invite import InviteActionOut, InviteCreateIn, InviteOut
from app.services import invite_service

router = APIRouter()


@router.post("", response_model=InviteOut)
def create_invite(
    data: InviteCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return invite_service.create_invite(db, current_user, data.model_dump(mode="json"))


@router.get("", response_model=list[InviteOut])
def list_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return invite_service.list_invites(db, current_user)


@router.post("/renew", response_model=InviteOut)
def renew_invite(
    data: InviteCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return invite_service.renew_invite(db, current_user, data.model_dump(mode="json"))


@router.post("/{invite_id}/revoke", response_model=InviteActionOut)
def revoke_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return invite_service.revoke_invite(db, current_user, invite_id)
