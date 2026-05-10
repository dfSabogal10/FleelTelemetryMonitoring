import logging

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone_count import ZoneCount

logger = logging.getLogger(__name__)


async def increment_zone_entry_count(session: AsyncSession, zone_id: str) -> None:
    """Atomically increment a zone counter in the database."""
    stmt = (
        update(ZoneCount)
        .where(ZoneCount.zone_id == zone_id)
        .values(
            entry_count=ZoneCount.entry_count + 1,
            updated_at=func.now(),
        )
    )
    await session.execute(stmt)
    logger.info("zone_count_incremented zone_id=%s", zone_id)
