"""系统相关 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class InitializedOut(BaseModel):
    initialized: bool
    allow_insecure_clipboard: bool = False


class InitIn(BaseModel):
    email: EmailStr
    nickname: str = Field(min_length=3, max_length=100)
    password: str
