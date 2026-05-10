from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.zone_count import ZoneCount
from app.schemas.zones import ZoneCountResponse

router = APIRouter()


@router.get("/zones/counts", response_model=list[ZoneCountResponse])
async def get_zone_counts(db: AsyncSession = Depends(get_db)) -> list[ZoneCountResponse]:
    stmt = select(ZoneCount).order_by(ZoneCount.zone_id.asc())
    records = (await db.execute(stmt)).scalars().all()
    return [
        ZoneCountResponse(zone_id=record.zone_id, entry_count=record.entry_count)
        for record in records
    ]
