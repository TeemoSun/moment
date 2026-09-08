"""进程内滑动窗口限流器（按 IP）。

单进程内存实现，重启即清零；多 worker 部署时每个 worker 独立计数，
对自托管单 worker 场景足够。键格式 "{scope}:{ip}"。
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.config import settings
from app.schemas.common import AppError, ErrorCode

_attempts: dict[str, deque[float]] = defaultdict(deque)
_MAX_KEYS = 100_000


def hit(scope: str, ip: str, limit: int, window_seconds: int) -> None:
    """记录一次尝试；窗口内超过 limit 次抛 429。测试可置 RATE_LIMIT_ENABLED=false 关闭。"""
    if not settings.RATE_LIMIT_ENABLED:
        return
    key = f"{scope}:{ip}"
    now = time.monotonic()
    q = _attempts[key]
    while q and q[0] <= now - window_seconds:
        q.popleft()
    if len(q) >= limit:
        retry_after = int(q[0] + window_seconds - now) + 1
        raise AppError(
            ErrorCode.RATE_LIMITED,
            "请求过于频繁，请稍后再试",
            429,
            {"retry_after_seconds": retry_after},
        )
    q.append(now)
    if len(_attempts) > _MAX_KEYS:
        _evict(now)


def _evict(now: float) -> None:
    expired = [k for k, q in _attempts.items() if not q or q[-1] <= now - 3600]
    for k in expired:
        del _attempts[k]
    if len(_attempts) > _MAX_KEYS:
        _attempts.clear()
