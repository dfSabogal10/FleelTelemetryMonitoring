from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import VehicleNotFoundError
from app.models.anomaly import Anomaly
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle
from app.schemas.telemetry import TelemetryIngestRequest, TelemetryIngestResponse
from app.services.anomaly import detect_anomalies
from app.services.fault_transition import FaultTransitionService
from app.services.zone_count import increment_zone_entry_count

logger = logging.getLogger(__name__)


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
        previous_event_stmt = (
            select(TelemetryEvent)
            .where(TelemetryEvent.vehicle_id == payload.vehicle_id)
            .order_by(TelemetryEvent.timestamp.desc())
            .limit(1)
        )
        previous_event = (await session.execute(previous_event_stmt)).scalar_one_or_none()

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

        is_stale = vehicle.last_seen_at is not None and payload.timestamp < vehicle.last_seen_at

        if payload.zone_entered is not None:
            await increment_zone_entry_count(session, payload.zone_entered)

        detected_anomalies = detect_anomalies(payload, previous_event)
        for anomaly in detected_anomalies:
            session.add(
                Anomaly(
                    vehicle_id=payload.vehicle_id,
                    telemetry_event_id=event.id,
                    anomaly_type=anomaly["type"],
                    severity=anomaly["severity"],
                    message=anomaly["message"],
                )
            )
            logger.warning(
                "anomaly_created vehicle_id=%s anomaly_type=%s severity=%s",
                payload.vehicle_id,
                anomaly["type"],
                anomaly["severity"],
            )

        if not is_stale:
            await FaultTransitionService.handle_fault_transition_if_needed(
                session=session,
                vehicle=vehicle,
                incoming_status=status_value,
            )
            vehicle.status = status_value
            vehicle.battery_pct = payload.battery_pct
            vehicle.speed_mps = payload.speed_mps
            vehicle.lat = payload.lat
            vehicle.lon = payload.lon
            vehicle.last_seen_at = payload.timestamp
        else:
            logger.warning(
                "stale_telemetry_persisted vehicle_id=%s telemetry_event_id=%s "
                "skipped_vehicle_state_update",
                payload.vehicle_id,
                event.id,
            )

        return TelemetryIngestResponse(telemetry_event_id=event.id)
