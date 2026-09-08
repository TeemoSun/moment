"""认证路由：RSA 公钥、注册、登录、登出、刷新。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, verify_csrf
from app.core.ratelimit import hit as rate_limit
from app.database import get_db
from app.models.users import User
from app.schemas.auth import LoginIn, RegisterIn, RSAKeyOut, TokenOut
from app.services import auth_service
from app.services.rsa_service import get_or_create_rsa_key
from app.services.user_service import user_to_me_out

router = APIRouter()


@router.get("/rsa-public-key", response_model=RSAKeyOut)
def get_rsa_public_key(db: Session = Depends(get_db)) -> RSAKeyOut:
    key = get_or_create_rsa_key(db)
    return RSAKeyOut(public_key=key.public_key_pem)


@router.post("/register", response_model=TokenOut)
def register(
    data: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenOut:
    rate_limit("register", request.client.host if request.client else "unknown", 5, 3600)
    user = auth_service.register(db, data)
    from app.core.cookies import generate_csrf_token, set_auth_cookies
    from app.core.jwt import create_access_token

    token = create_access_token(user.id, user.role, user.token_version)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)
    return TokenOut(user=user_to_me_out(user))


@router.post("/login", response_model=TokenOut)
def login(
    data: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenOut:
    rate_limit("login", request.client.host if request.client else "unknown", 10, 300)
    user = auth_service.login(db, data, response)
    return TokenOut(user=user_to_me_out(user))


@router.post("/logout")
def logout(
    response: Response,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    auth_service.logout(response)
    return {"message": "已登出"}


@router.post("/refresh", response_model=TokenOut)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> TokenOut:
    user = auth_service.refresh(db, current_user, response)
    return TokenOut(user=user_to_me_out(user))
