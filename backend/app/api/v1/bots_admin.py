"""管理后台机器人路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import require_admin, verify_csrf
from app.database import get_db
from app.schemas.bot import BotActionOut, BotAdminOut, BotCreateIn, BotUpdateIn
from app.services import bot_service

router = APIRouter()


@router.get("", response_model=list[BotAdminOut])
def list_bots(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> list[dict]:
    return bot_service.list_bots_admin(db)


@router.post("", response_model=BotAdminOut, status_code=201)
def create_bot(
    data: BotCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return bot_service.create_bot(db, data.model_dump(mode="json"))


@router.patch("/{bot_id}", response_model=BotAdminOut)
def update_bot(
    bot_id: int,
    data: BotUpdateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return bot_service.update_bot(db, bot_id, data.model_dump(mode="json", exclude_unset=True))


@router.delete("/{bot_id}", response_model=BotActionOut)
def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return bot_service.delete_bot(db, bot_id)


@router.post("/{bot_id}/avatar", response_model=BotActionOut)
def upload_bot_avatar(
    bot_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return bot_service.upload_bot_avatar(db, bot_id, file)


@router.post("/{bot_id}/trigger", response_model=BotActionOut)
def trigger_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return bot_service.trigger_bot(db, bot_id)
