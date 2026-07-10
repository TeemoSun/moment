from __future__ import annotations

from sqlalchemy import select

from app.config import get_settings
from app.logging_conf import logger
from app.models import InviteCode, User
from app.security import hash_password

settings = get_settings()


async def ensure_initial_admin(session_factory) -> None:
    """Seed an admin account + invite code on first startup if absent."""
    async with session_factory() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if admin is None:
            logger.info("Seeding initial admin account...")
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password(settings.INIT_ADMIN_PASSWORD),
                is_admin=True,
                is_active=True,
                display_name="管理员",
            )
            db.add(admin)
            await db.flush()

            invite = InviteCode(
                code=settings.INIT_ADMIN_INVITE_CODE,
                created_by=admin.id,
                max_uses=100,
            )
            db.add(invite)
            await db.commit()
            logger.info(
                "Admin seeded: username=admin  invite_code={}  "
                "(change password after first login!)",
                settings.INIT_ADMIN_INVITE_CODE,
            )
            return

        # Ensure an invite code exists even if admin was created elsewhere
        ic_result = await db.execute(
            select(InviteCode).where(InviteCode.code == settings.INIT_ADMIN_INVITE_CODE)
        )
        if ic_result.scalar_one_or_none() is None:
            invite = InviteCode(
                code=settings.INIT_ADMIN_INVITE_CODE,
                created_by=admin.id,
                max_uses=100,
            )
            db.add(invite)
            await db.commit()
            logger.info("Invite code {} ensured", settings.INIT_ADMIN_INVITE_CODE)