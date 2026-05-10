import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse
from app.services.telemetry import TelemetryService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/telemetry", response_model=TelemetryIngestResponse)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> TelemetryIngestResponse:
    try:
        response = await TelemetryService.ingest_event(db, payload)
        await db.commit()
        logger.info(
            "telemetry_accepted vehicle_id=%s telemetry_event_id=%s",
            payload.vehicle_id,
            response.telemetry_event_id,
        )
        return response
    except Exception:
        await db.rollback()
        raise
