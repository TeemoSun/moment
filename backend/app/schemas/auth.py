"""认证相关 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class RSAKeyOut(BaseModel):
    public_key: str


class RegisterIn(BaseModel):
    email: EmailStr
    nickname: str
    password: str
    invite_code: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    user: dict
