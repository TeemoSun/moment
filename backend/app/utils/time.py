"""时间工具：统一使用 naive UTC，与数据库存储保持一致。

仅用于"写入/比较数据库 DateTime 列"的场景，确保写入值与从 DB 读出的值类型一致
（均为 naive）。JWT 的 exp/iat 等场景仍应使用 aware UTC（datetime.now(UTC)）。
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """返回 naive UTC datetime（无 tzinfo），与数据库存储格式一致。"""
    return datetime.now(UTC).replace(tzinfo=None)
