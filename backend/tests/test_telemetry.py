from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from app.database import AsyncSessionLocal
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle


def _valid_payload(**overrides: object) -> dict:
    base: dict = {
        "vehicle_id": "v-12",
        "timestamp": "2026-05-09T12:00:00Z",
        "lat": 37.41,
        "lon": -122.08,
        "battery_pct": 78,
        "speed_mps": 1.2,
        "status": "moving",
        "error_codes": [],
        "zone_entered": None,
    }
    base.update(overrides)
    return base


@pytest.fixture
async def reset_vehicle_v12() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TelemetryEvent).where(TelemetryEvent.vehicle_id == "v-12"))
        vehicle = await session.get(Vehicle, "v-12")
        assert vehicle is not None
        vehicle.status = "idle"
        vehicle.battery_pct = None
        vehicle.speed_mps = None
        vehicle.lat = None
        vehicle.lon = None
        vehicle.last_seen_at = None
        await session.commit()


@pytest.mark.usefixtures("reset_vehicle_v12")
async def test_telemetry_success_persists_and_updates_vehicle(client: AsyncClient) -> None:
    response = await client.post("/telemetry", json=_valid_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    event_id = UUID(body["telemetry_event_id"])

    async with AsyncSessionLocal() as session:
        event = await session.get(TelemetryEvent, event_id)
        assert event is not None
        assert event.vehicle_id == "v-12"
        assert event.lat == 37.41
        assert event.lon == -122.08
        assert event.battery_pct == 78
        assert event.speed_mps == 1.2
        assert event.status == "moving"
        assert event.error_codes == []
        assert event.zone_entered is None

        vehicle = await session.get(Vehicle, "v-12")
        assert vehicle is not None
        assert vehicle.status == "moving"
        assert vehicle.battery_pct == 78
        assert vehicle.speed_mps == 1.2
        assert vehicle.lat == 37.41
        assert vehicle.lon == -122.08
        assert vehicle.last_seen_at is not None
        assert vehicle.last_seen_at == datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc)


async def test_unknown_vehicle_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/telemetry",
        json=_valid_payload(vehicle_id="v-99999"),
    )
    assert response.status_code == 404
    body = response.json()
    assert body == {
        "error": {
            "code": "vehicle_not_found",
            "message": "Vehicle v-99999 was not found",
        }
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "invalid_status"),
        ("battery_pct", -1),
        ("battery_pct", 101),
        ("speed_mps", -0.1),
        ("lat", 91),
        ("lat", -91),
        ("lon", 181),
        ("lon", -181),
    ],
)
async def test_field_validation_rejected(
    client: AsyncClient,
    field: str,
    value: object,
) -> None:
    payload = _valid_payload()
    payload[field] = value
    response = await client.post("/telemetry", json=payload)
    assert response.status_code == 422


async def test_unknown_zone_entered_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/telemetry",
        json=_valid_payload(zone_entered="not_a_real_zone"),
    )
    assert response.status_code == 422


@pytest.mark.usefixtures("reset_vehicle_v12")
async def test_stale_telemetry_persisted_but_does_not_overwrite_vehicle(client: AsyncClient) -> None:
    newer = await client.post(
        "/telemetry",
        json=_valid_payload(timestamp="2026-05-09T14:00:00Z", battery_pct=90),
    )
    assert newer.status_code == 200
    older = await client.post(
        "/telemetry",
        json=_valid_payload(
            timestamp="2026-05-09T12:00:00Z",
            battery_pct=10,
            status="idle",
        ),
    )
    assert older.status_code == 200

    newer_id = UUID(newer.json()["telemetry_event_id"])
    older_id = UUID(older.json()["telemetry_event_id"])
    assert newer_id != older_id

    async with AsyncSessionLocal() as session:
        count_stmt = select(func.count()).select_from(TelemetryEvent).where(
            TelemetryEvent.vehicle_id == "v-12"
        )
        count = (await session.execute(count_stmt)).scalar_one()
        assert count == 2

        vehicle = await session.get(Vehicle, "v-12")
        assert vehicle is not None
        assert vehicle.battery_pct == 90
        assert vehicle.status == "moving"
        assert vehicle.last_seen_at == datetime(2026, 5, 9, 14, 0, tzinfo=timezone.utc)
