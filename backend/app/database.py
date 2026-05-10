from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - register SQLAlchemy models with Base.metadata
from app.config import get_settings
from app.models.base import Base

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.sql_echo,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create database tables if they do not exist (MVP; Alembic can replace this later)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
