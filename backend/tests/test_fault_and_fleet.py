from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from app.database import AsyncSessionLocal
from app.models.maintenance_record import MaintenanceRecord
from app.models.mission import Mission
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle


def _payload(
    *,
    vehicle_id: str,
    timestamp: str,
    status: str,
    battery_pct: int = 50,
    speed_mps: float = 0.0,
    lat: float = 37.41,
    lon: float = -122.08,
    error_codes: list[str] | None = None,
    zone_entered: str | None = None,
) -> dict:
    return {
        "vehicle_id": vehicle_id,
        "timestamp": timestamp,
        "lat": lat,
        "lon": lon,
        "battery_pct": battery_pct,
        "speed_mps": speed_mps,
        "status": status,
        "error_codes": error_codes or [],
        "zone_entered": zone_entered,
    }


@pytest.fixture
async def reset_fault_fleet_state() -> None:
    vehicle_ids = ["v-20", "v-21", "v-22", "v-23", "v-24", "v-25", "v-26", "v-27", "v-28", "v-29"]
    async with AsyncSessionLocal() as session:
        await session.execute(delete(MaintenanceRecord).where(MaintenanceRecord.vehicle_id.in_(vehicle_ids)))
        await session.execute(delete(TelemetryEvent).where(TelemetryEvent.vehicle_id.in_(vehicle_ids)))

        for vehicle_id in vehicle_ids:
            vehicle = await session.get(Vehicle, vehicle_id)
            assert vehicle is not None
            vehicle.status = "idle"
            vehicle.battery_pct = None
            vehicle.speed_mps = None
            vehicle.lat = None
            vehicle.lon = None
            vehicle.last_seen_at = None

            missions = (
                await session.execute(
                    select(Mission).where(Mission.vehicle_id == vehicle_id).order_by(Mission.started_at.asc())
                )
            ).scalars().all()
            assert missions
            first_active = missions[0]
            first_active.status = "active"
            first_active.completed_at = None
            first_active.cancelled_at = None
            first_active.cancel_reason = None
            for mission in missions[1:]:
                mission.status = "cancelled"
                mission.cancelled_at = datetime.now(UTC)
                mission.cancel_reason = "test_reset"
                mission.completed_at = None

        await session.commit()


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_fault_transition_cancels_mission_and_creates_maintenance(client: AsyncClient) -> None:
    moving_response = await client.post(
        "/telemetry",
        json=_payload(vehicle_id="v-20", timestamp="2026-05-09T12:00:00Z", status="moving"),
    )
    assert moving_response.status_code == 200

    fault_response = await client.post(
        "/telemetry",
        json=_payload(
            vehicle_id="v-20",
            timestamp="2026-05-09T12:00:01Z",
            status="fault",
            error_codes=["E_STOP"],
        ),
    )
    assert fault_response.status_code == 200

    async with AsyncSessionLocal() as session:
        vehicle = await session.get(Vehicle, "v-20")
        assert vehicle is not None
        assert vehicle.status == "fault"

        cancelled_missions = (
            await session.execute(
                select(Mission).where(Mission.vehicle_id == "v-20", Mission.status == "cancelled")
            )
        ).scalars().all()
        assert cancelled_missions
        assert any(m.cancel_reason == "vehicle_fault" for m in cancelled_missions)

        maintenance_records = (
            await session.execute(select(MaintenanceRecord).where(MaintenanceRecord.vehicle_id == "v-20"))
        ).scalars().all()
        assert len(maintenance_records) == 1
        assert maintenance_records[0].reason == "vehicle_fault"


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_repeated_fault_telemetry_does_not_duplicate_maintenance(client: AsyncClient) -> None:
    for ts in ["2026-05-09T12:00:00Z", "2026-05-09T12:00:01Z", "2026-05-09T12:00:02Z"]:
        response = await client.post(
            "/telemetry",
            json=_payload(vehicle_id="v-21", timestamp=ts, status="fault", error_codes=["E_STOP"]),
        )
        assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        maintenance_count = (
            await session.execute(
                select(func.count())
                .select_from(MaintenanceRecord)
                .where(MaintenanceRecord.vehicle_id == "v-21")
            )
        ).scalar_one()
        assert maintenance_count == 1

        fault_cancelled_count = (
            await session.execute(
                select(func.count())
                .select_from(Mission)
                .where(
                    Mission.vehicle_id == "v-21",
                    Mission.status == "cancelled",
                    Mission.cancel_reason == "vehicle_fault",
                )
            )
        ).scalar_one()
        assert fault_cancelled_count == 1


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_concurrent_fault_telemetry_single_side_effect_set(client: AsyncClient) -> None:
    async def post_fault(i: int) -> int:
        response = await client.post(
            "/telemetry",
            json=_payload(
                vehicle_id="v-22",
                timestamp=f"2026-05-09T12:00:{i:02d}Z",
                status="fault",
                error_codes=["E_STOP"],
            ),
        )
        return response.status_code

    statuses = await asyncio.gather(*[post_fault(i) for i in range(8)])
    assert all(code == 200 for code in statuses)

    async with AsyncSessionLocal() as session:
        vehicle = await session.get(Vehicle, "v-22")
        assert vehicle is not None
        assert vehicle.status == "fault"

        maintenance_count = (
            await session.execute(
                select(func.count())
                .select_from(MaintenanceRecord)
                .where(MaintenanceRecord.vehicle_id == "v-22")
            )
        ).scalar_one()
        assert maintenance_count == 1

        fault_cancelled_count = (
            await session.execute(
                select(func.count())
                .select_from(Mission)
                .where(
                    Mission.vehicle_id == "v-22",
                    Mission.status == "cancelled",
                    Mission.cancel_reason == "vehicle_fault",
                )
            )
        ).scalar_one()
        assert fault_cancelled_count == 1


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_fleet_state_matches_persisted_vehicle_counts(client: AsyncClient) -> None:
    updates = [
        ("v-23", "moving", "2026-05-09T12:10:00Z"),
        ("v-24", "charging", "2026-05-09T12:10:01Z"),
        ("v-25", "fault", "2026-05-09T12:10:02Z"),
    ]
    for vehicle_id, status, ts in updates:
        response = await client.post(
            "/telemetry",
            json=_payload(vehicle_id=vehicle_id, timestamp=ts, status=status),
        )
        assert response.status_code == 200

    fleet_response = await client.get("/fleet/state")
    assert fleet_response.status_code == 200
    endpoint_counts = fleet_response.json()

    async with AsyncSessionLocal() as session:
        db_rows = (
            await session.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status))
        ).all()
    db_counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
    for status, count in db_rows:
        if status in db_counts:
            db_counts[status] = int(count)
    assert endpoint_counts == db_counts


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_concurrent_fleet_state_matches_db_counts(client: AsyncClient) -> None:
    statuses = ["moving", "charging", "idle", "fault", "moving", "charging"]
    vehicle_ids = ["v-20", "v-21", "v-22", "v-23", "v-24", "v-25"]

    async def post_status(i: int) -> int:
        response = await client.post(
            "/telemetry",
            json=_payload(
                vehicle_id=vehicle_ids[i],
                timestamp=f"2026-05-09T12:20:{i:02d}Z",
                status=statuses[i],
            ),
        )
        return response.status_code

    result_codes = await asyncio.gather(*[post_status(i) for i in range(len(vehicle_ids))])
    assert all(code == 200 for code in result_codes)

    fleet_response = await client.get("/fleet/state")
    assert fleet_response.status_code == 200
    endpoint_counts = fleet_response.json()

    async with AsyncSessionLocal() as session:
        db_rows = (
            await session.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status))
        ).all()
    db_counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
    for status, count in db_rows:
        if status in db_counts:
            db_counts[status] = int(count)
    assert endpoint_counts == db_counts


@pytest.mark.usefixtures("reset_fault_fleet_state")
async def test_get_vehicles_returns_sorted_seeded_and_updated_state(client: AsyncClient) -> None:
    update_response = await client.post(
        "/telemetry",
        json=_payload(
            vehicle_id="v-26",
            timestamp="2026-05-09T12:30:00Z",
            status="moving",
            battery_pct=88,
            speed_mps=1.7,
            lat=37.42,
            lon=-122.09,
        ),
    )
    assert update_response.status_code == 200

    response = await client.get("/vehicles")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) == 50

    returned_ids = [item["vehicle_id"] for item in vehicles]
    assert returned_ids == sorted(returned_ids)

    vehicle_26 = next(item for item in vehicles if item["vehicle_id"] == "v-26")
    assert vehicle_26["status"] == "moving"
    assert vehicle_26["battery_pct"] == 88
    assert vehicle_26["speed_mps"] == 1.7
    assert vehicle_26["lat"] == 37.42
    assert vehicle_26["lon"] == -122.09
    assert vehicle_26["last_seen_at"] in {"2026-05-09T12:30:00Z", "2026-05-09T12:30:00+00:00"}
