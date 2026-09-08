"""机器人调度器：APScheduler，单进程文件锁。"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from app.config import PROJECT_ROOT

logger = logging.getLogger("app.scheduler")

_scheduler = None
_lock_fd = None
_is_master = False


def _try_acquire_lock() -> bool:
    global _lock_fd, _is_master
    import fcntl

    lock_path = (PROJECT_ROOT / "data" / ".bot_scheduler.lock").resolve()
    if PROJECT_ROOT.resolve() not in lock_path.parents:
        raise RuntimeError("lock path escaped project root")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _lock_fd = lock_path.open("w")
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _is_master = True
        return True
    except OSError:
        _is_master = False
        if _lock_fd:
            _lock_fd.close()
            _lock_fd = None
        return False


def start_scheduler() -> None:
    global _scheduler
    if not _try_acquire_lock():
        logger.info("bot scheduler: another worker holds the lock, skipping")
        return
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        logger.warning("apscheduler not installed, bot scheduler disabled")
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    logger.info("bot scheduler started (master)")
    from app.database import SessionLocal
    from app.models.bots import Bot

    db = SessionLocal()
    try:
        bots = db.query(Bot).filter(Bot.enabled.is_(True), Bot.auto_paused.is_(False)).all()
        for bot in bots:
            _schedule_next(bot.user_id, bot.poll_interval_n, bot.poll_interval_x)
    finally:
        db.close()


def _schedule_next(bot_user_id: int, n: int, x: int) -> None:
    if _scheduler is None:
        return
    from apscheduler.triggers.date import DateTrigger

    delay = random.randint(max(1, n - x), n + x)
    run_at = datetime.now() + timedelta(seconds=delay)
    _scheduler.add_job(
        _run_and_reschedule,
        DateTrigger(run_date=run_at),
        args=[bot_user_id, n, x],
        id=f"bot_{bot_user_id}",
        replace_existing=True,
    )


async def _run_and_reschedule(bot_user_id: int, n: int, x: int) -> None:
    from app.services.bot_engine import run_bot

    try:
        await run_bot(bot_user_id)
    except Exception:
        logger.exception("run_bot %s failed", bot_user_id)
    from app.database import SessionLocal
    from app.models.bots import Bot

    db = SessionLocal()
    try:
        bot = db.query(Bot).filter(Bot.user_id == bot_user_id).first()
        if bot and bot.enabled and not bot.auto_paused:
            _schedule_next(bot_user_id, bot.poll_interval_n, bot.poll_interval_x)
    finally:
        db.close()


def reschedule_bot(bot_user_id: int, n: int, x: int) -> None:
    if _scheduler is None:
        return
    _schedule_next(bot_user_id, n, x)


def trigger_bot_now(bot_user_id: int) -> None:
    if _scheduler is None:
        return
    from apscheduler.triggers.date import DateTrigger

    from app.database import SessionLocal
    from app.models.bots import Bot

    db = SessionLocal()
    try:
        bot = db.query(Bot).filter(Bot.user_id == bot_user_id).first()
        if not bot:
            return
        n = bot.poll_interval_n
        x = bot.poll_interval_x
    finally:
        db.close()
    _scheduler.add_job(
        _run_and_reschedule,
        DateTrigger(run_date=datetime.now()),
        args=[bot_user_id, n, x],
        id=f"bot_now_{bot_user_id}",
        replace_existing=True,
    )


def stop_scheduler() -> None:
    global _scheduler, _lock_fd, _is_master
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _lock_fd:
        import fcntl

        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        _lock_fd.close()
        _lock_fd = None
    _is_master = False
