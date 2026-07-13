"""系统路由：初始化判定与执行。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.cookies import generate_csrf_token, set_auth_cookies
from app.core.jwt import create_access_token
from app.database import get_db
from app.schemas.auth import TokenOut
from app.schemas.system import InitializedOut, InitIn
from app.services import system_service
from app.services.user_service import user_to_me_out

router = APIRouter()


@router.get("/initialized", response_model=InitializedOut)
def check_initialized(db: Session = Depends(get_db)) -> InitializedOut:
    return InitializedOut(initialized=system_service.is_initialized(db))


@router.post("/init", response_model=TokenOut)
def init_system(
    data: InitIn,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenOut:
    user = system_service.init_system(db, data)
    token = create_access_token(user.id, user.role)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)
    return TokenOut(user=user_to_me_out(user))
