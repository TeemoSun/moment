"""机器人相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BotCreateIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=100)
    persona: str = Field(min_length=1, max_length=2000)
    poll_interval_n: int = Field(default=600, ge=1)
    poll_interval_x: int = Field(default=60, ge=0)
    lookback_days: int = Field(default=3, ge=1)
    comments_per_hour: int = Field(default=10, ge=1)
    max_consecutive_failures: int = Field(default=5, ge=1)
    llm_model: str | None = Field(default=None, max_length=100)


class BotUpdateIn(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    persona: str | None = Field(default=None, min_length=1, max_length=2000)
    poll_interval_n: int | None = Field(default=None, ge=1)
    poll_interval_x: int | None = Field(default=None, ge=0)
    lookback_days: int | None = Field(default=None, ge=1)
    comments_per_hour: int | None = Field(default=None, ge=1)
    max_consecutive_failures: int | None = Field(default=None, ge=1)
    llm_model: str | None = Field(default=None, max_length=100)
    enabled: bool | None = None
    restore: bool | None = None


class BotAdminOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    email: str
    avatar_url: str
    persona: str
    poll_interval_n: int
    poll_interval_x: int
    lookback_days: int
    comments_per_hour: int
    max_consecutive_failures: int
    llm_model: str | None
    enabled: bool
    auto_paused: bool
    consecutive_failures: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime


class BotPublicOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    avatar_url: str
    persona_brief: str
    is_friend: bool


class BotActionOut(BaseModel):
    message: str
