from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.anomaly import Anomaly
from app.schemas.anomalies import AnomalyQueryParams, AnomalyResponse

router = APIRouter()


@router.get("/anomalies", response_model=list[AnomalyResponse])
async def get_anomalies(
    vehicle_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[AnomalyResponse]:
    params = AnomalyQueryParams(
        vehicle_id=vehicle_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    stmt = select(Anomaly)
    if params.vehicle_id is not None:
        stmt = stmt.where(Anomaly.vehicle_id == params.vehicle_id)
    if params.start_time is not None:
        stmt = stmt.where(Anomaly.created_at >= params.start_time)
    if params.end_time is not None:
        stmt = stmt.where(Anomaly.created_at <= params.end_time)

    stmt = stmt.order_by(Anomaly.created_at.desc()).limit(params.limit)
    anomalies = (await db.execute(stmt)).scalars().all()
    return [
        AnomalyResponse(
            id=anomaly.id,
            vehicle_id=anomaly.vehicle_id,
            type=anomaly.anomaly_type,
            severity=anomaly.severity,
            message=anomaly.message,
            created_at=anomaly.created_at,
        )
        for anomaly in anomalies
    ]
