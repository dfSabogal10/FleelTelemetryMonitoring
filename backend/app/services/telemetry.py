from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import VehicleNotFoundError
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle
from app.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse


class TelemetryService:
    @staticmethod
    async def ingest_event(
        session: AsyncSession,
        payload: TelemetryIngestRequest,
    ) -> TelemetryIngestResponse:
        """Persist telemetry and update vehicle state when the event is not stale."""
        lock_stmt = select(Vehicle).where(Vehicle.id == payload.vehicle_id).with_for_update()
        result = await session.execute(lock_stmt)
        vehicle = result.scalar_one_or_none()
        if vehicle is None:
            raise VehicleNotFoundError(payload.vehicle_id)

        status_value = payload.status.value

        event = TelemetryEvent(
            vehicle_id=payload.vehicle_id,
            timestamp=payload.timestamp,
            lat=payload.lat,
            lon=payload.lon,
            battery_pct=payload.battery_pct,
            speed_mps=payload.speed_mps,
            status=status_value,
            error_codes=payload.error_codes,
            zone_entered=payload.zone_entered,
        )
        session.add(event)
        await session.flush()

        if vehicle.last_seen_at is None or payload.timestamp >= vehicle.last_seen_at:
            vehicle.status = status_value
            vehicle.battery_pct = payload.battery_pct
            vehicle.speed_mps = payload.speed_mps
            vehicle.lat = payload.lat
            vehicle.lon = payload.lon
            vehicle.last_seen_at = payload.timestamp

        return TelemetryIngestResponse(telemetry_event_id=event.id)
