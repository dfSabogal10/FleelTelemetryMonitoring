"""
E2E-style ingestion smoke test (correctness, not a throughput benchmark).

Simulates 50 vehicles emitting telemetry at 1 Hz for 3 logical seconds (3 ticks)
using concurrent HTTP requests per tick. Validates persistence, zone counters,
anomalies, fleet aggregates, and fault side effects under concurrency — without
real time sleeps or performance assertions.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from app.database import AsyncSessionLocal
from app.models.anomaly import Anomaly
from app.models.maintenance_record import MaintenanceRecord
from app.models.mission import Mission
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle
from app.models.zone_count import ZoneCount

VEHICLE_IDS = [f"v-{i}" for i in range(1, 51)]
BASE_TIME = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
TICKS = 3
EXPECTED_TELEMETRY_DELTA = len(VEHICLE_IDS) * TICKS  # 150

# Zone entry expectations (from deterministic rules below)
EXPECTED_CHARGING_BAY_1_INCREMENT = 10  # v-1..5 tick 0, v-6..10 tick 1
EXPECTED_MAINTENANCE_BAY_INCREMENT = 5  # v-11..15 tick 2


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _event_time(tick: int, vehicle_index: int) -> datetime:
    """Logical second `tick` (0..2) plus sub-second offset per vehicle for stable ordering."""
    return BASE_TIME + timedelta(seconds=tick, milliseconds=vehicle_index)


def _build_payload(vehicle_index: int, tick: int) -> dict:
    """vehicle_index: 1..50. tick: 0..2."""
    vid = f"v-{vehicle_index}"
    ts = _event_time(tick, vehicle_index)
    payload: dict = {
        "vehicle_id": vid,
        "timestamp": _iso_z(ts),
        "lat": 37.4 + vehicle_index * 1e-4,
        "lon": -122.08 + vehicle_index * 1e-4,
        "battery_pct": 80,
        "speed_mps": 1.2,
        "status": "moving",
        "error_codes": [],
        "zone_entered": None,
    }

    # Zone entries
    if 1 <= vehicle_index <= 5 and tick == 0:
        payload["zone_entered"] = "charging_bay_1"
    elif 6 <= vehicle_index <= 10 and tick == 1:
        payload["zone_entered"] = "charging_bay_1"
    elif 11 <= vehicle_index <= 15 and tick == 2:
        payload["zone_entered"] = "maintenance_bay"

    # Fault transition: non-fault then fault (repeated fault on tick 2)
    if vehicle_index in (20, 21):
        if tick == 0:
            payload["status"] = "moving"
        elif tick == 1:
            payload["status"] = "fault"
            payload["speed_mps"] = 0.0
            payload["error_codes"] = ["E_STOP"]
        else:
            payload["status"] = "fault"
            payload["speed_mps"] = 0.0
            payload["error_codes"] = ["E_STOP"]

    # Anomaly triggers (single tick each; later ticks back to nominal moving values)
    if vehicle_index == 30:
        if tick == 0:
            payload["battery_pct"] = 10
        else:
            payload["battery_pct"] = 80
    if vehicle_index == 31:
        if tick == 0:
            payload["speed_mps"] = 6.0
        else:
            payload["speed_mps"] = 1.2
    if vehicle_index == 32:
        if tick == 0:
            payload["error_codes"] = ["E_TEST"]
        else:
            payload["error_codes"] = []

    # Mix of terminal statuses (last tick wins for vehicle row)
    if vehicle_index in (48, 49, 50) and tick == 2:
        payload["status"] = "idle"
    if vehicle_index in (46, 47) and tick == 2:
        payload["status"] = "charging"

    return payload


@pytest.fixture
async def reset_for_fleet_ingestion_smoke() -> None:
    """Deterministic DB slice for this scenario (fleet vehicles only)."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(MaintenanceRecord).where(MaintenanceRecord.vehicle_id.in_(VEHICLE_IDS)))
        await session.execute(delete(Anomaly).where(Anomaly.vehicle_id.in_(VEHICLE_IDS)))
        await session.execute(delete(TelemetryEvent).where(TelemetryEvent.vehicle_id.in_(VEHICLE_IDS)))
        await session.execute(delete(Mission).where(Mission.vehicle_id.in_(VEHICLE_IDS)))

        for vid in VEHICLE_IDS:
            session.add(
                Mission(
                    vehicle_id=vid,
                    status="active",
                    started_at=datetime.now(UTC),
                )
            )

        for vid in VEHICLE_IDS:
            vehicle = await session.get(Vehicle, vid)
            assert vehicle is not None
            vehicle.status = "idle"
            vehicle.battery_pct = None
            vehicle.speed_mps = None
            vehicle.lat = None
            vehicle.lon = None
            vehicle.last_seen_at = None

        z1 = await session.get(ZoneCount, "charging_bay_1")
        z2 = await session.get(ZoneCount, "maintenance_bay")
        assert z1 is not None and z2 is not None
        z1.entry_count = 0
        z2.entry_count = 0

        await session.commit()


@pytest.mark.usefixtures("reset_for_fleet_ingestion_smoke")
async def test_fleet_ingestion_smoke_concurrent_ticks(client: AsyncClient) -> None:
    async with AsyncSessionLocal() as session:
        telemetry_before = (
            await session.execute(select(func.count()).select_from(TelemetryEvent))
        ).scalar_one()
        charging_before = (await session.get(ZoneCount, "charging_bay_1")).entry_count
        maint_before = (await session.get(ZoneCount, "maintenance_bay")).entry_count

    for tick in range(TICKS):
        payloads = [_build_payload(i, tick) for i in range(1, 51)]

        async def post_one(body: dict) -> int:
            r = await client.post("/telemetry", json=body)
            return r.status_code

        codes = await asyncio.gather(*[post_one(p) for p in payloads])
        assert all(c == 200 for c in codes), f"tick {tick} failures: {codes}"

    async with AsyncSessionLocal() as session:
        telemetry_after = (
            await session.execute(select(func.count()).select_from(TelemetryEvent))
        ).scalar_one()
        assert telemetry_after - telemetry_before == EXPECTED_TELEMETRY_DELTA

        charging_after = (await session.get(ZoneCount, "charging_bay_1")).entry_count
        maint_after = (await session.get(ZoneCount, "maintenance_bay")).entry_count
        assert charging_after - charging_before == EXPECTED_CHARGING_BAY_1_INCREMENT
        assert maint_after - maint_before == EXPECTED_MAINTENANCE_BAY_INCREMENT

        types_stmt = select(Anomaly.anomaly_type).where(Anomaly.vehicle_id.in_(VEHICLE_IDS))
        types_found = {row[0] for row in (await session.execute(types_stmt)).all()}
        assert {"fault_status", "low_battery", "excessive_speed", "error_codes_reported"} <= types_found

        for vid in ("v-20", "v-21"):
            vehicle = await session.get(Vehicle, vid)
            assert vehicle is not None
            assert vehicle.status == "fault"

            maint_count = (
                await session.execute(
                    select(func.count())
                    .select_from(MaintenanceRecord)
                    .where(MaintenanceRecord.vehicle_id == vid)
                )
            ).scalar_one()
            assert maint_count == 1

            fault_cancelled = (
                await session.execute(
                    select(func.count())
                    .select_from(Mission)
                    .where(
                        Mission.vehicle_id == vid,
                        Mission.status == "cancelled",
                        Mission.cancel_reason == "vehicle_fault",
                    )
                )
            ).scalar_one()
            assert fault_cancelled == 1

        db_rows = (
            await session.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status))
        ).all()
        db_counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
        for status, count in db_rows:
            if status in db_counts:
                db_counts[status] = int(count)

    fleet_resp = await client.get("/fleet/state")
    assert fleet_resp.status_code == 200
    assert fleet_resp.json() == db_counts
