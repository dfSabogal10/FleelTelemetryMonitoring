from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance_record import MaintenanceRecord
from app.models.mission import Mission
from app.models.vehicle import Vehicle

logger = logging.getLogger(__name__)


class FaultTransitionService:
    @staticmethod
    async def handle_fault_transition_if_needed(
        session: AsyncSession,
        vehicle: Vehicle,
        incoming_status: str,
    ) -> None:
        """Apply one-time mission cancellation + maintenance side effects on non-fault -> fault transition."""
        if incoming_status != "fault":
            return
        if vehicle.status == "fault":
            return

        logger.warning("vehicle_transitioned_to_fault vehicle_id=%s", vehicle.id)

        mission_stmt = (
            select(Mission)
            .where(Mission.vehicle_id == vehicle.id, Mission.status == "active")
            .order_by(Mission.started_at.desc())
            .limit(1)
            .with_for_update()
        )
        active_mission = (await session.execute(mission_stmt)).scalar_one_or_none()

        if active_mission is not None:
            now_utc = datetime.now(UTC)
            active_mission.status = "cancelled"
            active_mission.cancelled_at = now_utc
            active_mission.cancel_reason = "vehicle_fault"

            logger.warning(
                "active_mission_cancelled mission_id=%s vehicle_id=%s",
                active_mission.id,
                vehicle.id,
            )

            session.add(
                MaintenanceRecord(
                    vehicle_id=vehicle.id,
                    mission_id=active_mission.id,
                    reason="vehicle_fault",
                )
            )
            logger.warning(
                "maintenance_record_created vehicle_id=%s mission_id=%s",
                vehicle.id,
                active_mission.id,
            )
