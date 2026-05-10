"""Idempotent seed data for local development and demos."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.zones import ZONES
from app.models.mission import Mission
from app.models.vehicle import Vehicle
from app.models.zone_count import ZoneCount


async def seed_database(session: AsyncSession) -> None:
    await _seed_zone_counts(session)
    await _seed_vehicles(session)
    await _seed_active_missions(session)


async def _seed_zone_counts(session: AsyncSession) -> None:
    for zone_id in ZONES:
        existing = await session.get(ZoneCount, zone_id)
        if existing is None:
            session.add(ZoneCount(zone_id=zone_id, entry_count=0))


async def _seed_vehicles(session: AsyncSession) -> None:
    for i in range(1, 51):
        vehicle_id = f"v-{i}"
        existing = await session.get(Vehicle, vehicle_id)
        if existing is None:
            session.add(Vehicle(id=vehicle_id, status="idle"))


async def _seed_active_missions(session: AsyncSession) -> None:
    for i in range(1, 51):
        vehicle_id = f"v-{i}"
        stmt = (
            select(Mission.id)
            .where(Mission.vehicle_id == vehicle_id, Mission.status == "active")
            .limit(1)
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            continue
        session.add(
            Mission(
                vehicle_id=vehicle_id,
                status="active",
                started_at=datetime.now(timezone.utc),
            )
        )
