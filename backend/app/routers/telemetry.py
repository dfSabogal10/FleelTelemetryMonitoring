from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import VehicleNotFoundError
from app.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse
from app.services.telemetry import TelemetryService

router = APIRouter()


@router.post("/telemetry", response_model=TelemetryIngestResponse)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> TelemetryIngestResponse:
    try:
        response = await TelemetryService.ingest_event(db, payload)
        await db.commit()
        return response
    except VehicleNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
