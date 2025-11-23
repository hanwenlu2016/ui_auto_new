import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalars().first()
        if not user:
            user = User(
                email="admin@163.com",
                hashed_password=get_password_hash("admin"),
                full_name="Initial Admin",
                is_superuser=True,
                role="admin",
            )
            session.add(user)
            await session.commit()
            logger.info("Superuser created")
        else:
            logger.info("Superuser already exists")

async def main() -> None:
    logger.info("Creating initial data")
    await init_db()
    logger.info("Initial data created")

if __name__ == "__main__":
    asyncio.run(main())
