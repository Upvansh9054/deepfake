from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from typing import AsyncGenerator
import logging

logger = logging.getLogger("deepfake_shield.db")

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True if not is_sqlite else False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initializes tables in database and ensures default demo analyst credentials exist."""
    async with engine.begin() as conn:
        # Import models so Base has all metadata
        import app.models.entities  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified and tables created.")

    try:
        from app.models.entities import User
        from app.core.security import get_password_hash
        from sqlalchemy.future import select
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.email == "analyst@shield.ai"))
            if not res.scalars().first():
                session.add(User(
                    email="analyst@shield.ai",
                    hashed_password=get_password_hash("CyberSecurity2026!"),
                    full_name="Alex Mercer (Lead Threat Analyst)",
                    role="admin"
                ))
                await session.commit()
                logger.info("Default analyst demo profile seeded.")
    except Exception as e:
        logger.warning(f"Default demo user initialization skipped: {e}")
