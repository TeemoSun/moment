"""邀请码服务:生成、列表、失效、续期。"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.invite_codes import InviteCode
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.schemas.invite import InviteActionOut, InviteOut
from app.utils.time import utcnow

INVITE_CODE_LENGTH = 8
_INVITE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_invite_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
        existing = db.query(InviteCode).filter(InviteCode.code == code).first()
        if not existing:
            return code
    raise AppError(ErrorCode.INTERNAL, "Failed to generate unique invite code", 500)


def _compute_expires_at(duration_days: int | None) -> datetime | None:
    if duration_days is None:
        return None
    return utcnow() + timedelta(days=duration_days)


def _sync_expired(db: Session, creator_id: int) -> None:
    now = utcnow()
    db.query(InviteCode).filter(
        InviteCode.creator_id == creator_id,
        InviteCode.status == "active",
        InviteCode.expires_at.isnot(None),
        InviteCode.expires_at <= now,
    ).update({"status": "expired"}, synchronize_session="fetch")
    db.commit()


def create_invite(db: Session, user: User, data: dict) -> dict:
    if not user.can_invite:
        raise AppError(ErrorCode.INVITE_DISABLED, "Invite permission disabled", 403)
    _sync_expired(db, user.id)
    active = (
        db.query(InviteCode)
        .filter(InviteCode.creator_id == user.id, InviteCode.status == "active")
        .first()
    )
    if active:
        raise AppError(
            ErrorCode.ACTIVE_INVITE_EXISTS,
            "Active invite already exists, revoke or renew first",
            400,
        )
    code = generate_invite_code(db)
    expires_at = _compute_expires_at(data.get("duration_days"))
    invite = InviteCode(
        creator_id=user.id,
        code=code,
        status="active",
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return InviteOut(
        id=invite.id,
        code=invite.code,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        used_by_id=invite.used_by_id,
    ).model_dump(mode="json")


def list_invites(db: Session, user: User) -> list[dict]:
    _sync_expired(db, user.id)
    rows = (
        db.query(InviteCode)
        .filter(InviteCode.creator_id == user.id)
        .order_by(InviteCode.created_at.desc())
        .all()
    )
    return [
        InviteOut(
            id=r.id,
            code=r.code,
            status=r.status,
            expires_at=r.expires_at,
            created_at=r.created_at,
            used_by_id=r.used_by_id,
        ).model_dump(mode="json")
        for r in rows
    ]


def revoke_invite(db: Session, user: User, invite_id: int) -> dict:
    invite = db.query(InviteCode).filter(InviteCode.id == invite_id).first()
    if not invite or invite.creator_id != user.id:
        raise AppError(ErrorCode.INVITE_NOT_FOUND, "Invite not found", 404)
    if invite.status == "used":
        raise AppError(ErrorCode.INVITE_ALREADY_USED, "Used invite cannot be revoked", 400)
    if invite.status in ("revoked", "expired"):
        return {"message": "Invite already inactive"}
    invite.status = "revoked"
    db.commit()
    return InviteActionOut(message="Invite revoked").model_dump(mode="json")


def renew_invite(db: Session, user: User, data: dict) -> dict:
    if not user.can_invite:
        raise AppError(ErrorCode.INVITE_DISABLED, "Invite permission disabled", 403)
    _sync_expired(db, user.id)
    active = (
        db.query(InviteCode)
        .filter(InviteCode.creator_id == user.id, InviteCode.status == "active")
        .first()
    )
    if not active:
        raise AppError(
            ErrorCode.INVITE_NOT_FOUND,
            "No active invite to renew, create one first",
            404,
        )
    duration_days = data.get("duration_days")
    if duration_days is None:
        active.expires_at = None
    else:
        now = utcnow()
        base = active.expires_at if active.expires_at and active.expires_at > now else now
        active.expires_at = base + timedelta(days=duration_days)
    db.commit()
    db.refresh(active)
    return InviteOut(
        id=active.id,
        code=active.code,
        status=active.status,
        expires_at=active.expires_at,
        created_at=active.created_at,
        used_by_id=active.used_by_id,
    ).model_dump(mode="json")
