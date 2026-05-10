from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, update

from app.database import AsyncSessionLocal
from app.models.anomaly import Anomaly
from app.models.telemetry_event import TelemetryEvent
from app.models.vehicle import Vehicle
from app.models.zone_count import ZoneCount


def _payload(
    *,
    vehicle_id: str = "v-12",
    timestamp: str = "2026-05-09T12:00:00Z",
    lat: float = 37.41,
    lon: float = -122.08,
    battery_pct: int = 78,
    speed_mps: float = 1.2,
    status: str = "moving",
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
async def reset_zone_and_anomaly_state() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Anomaly).where(Anomaly.vehicle_id.in_(["v-12", "v-13", "v-14", "v-15"]))
        )
        await session.execute(
            delete(TelemetryEvent).where(
                TelemetryEvent.vehicle_id.in_(["v-12", "v-13", "v-14", "v-15"])
            )
        )
        await session.execute(
            update(ZoneCount)
            .where(ZoneCount.zone_id == "charging_bay_1")
            .values(entry_count=0)
        )
        for vehicle_id in ["v-12", "v-13", "v-14", "v-15"]:
            vehicle = await session.get(Vehicle, vehicle_id)
            assert vehicle is not None
            vehicle.status = "idle"
            vehicle.battery_pct = None
            vehicle.speed_mps = None
            vehicle.lat = None
            vehicle.lon = None
            vehicle.last_seen_at = None
        await session.commit()


@pytest.mark.usefixtures("reset_zone_and_anomaly_state")
async def test_zone_single_increment(client: AsyncClient) -> None:
    response = await client.post(
        "/telemetry",
        json=_payload(zone_entered="charging_bay_1"),
    )
    assert response.status_code == 200

    zone_counts = await client.get("/zones/counts")
    assert zone_counts.status_code == 200
    counts_by_zone = {item["zone_id"]: item["entry_count"] for item in zone_counts.json()}
    assert counts_by_zone["charging_bay_1"] == 1


@pytest.mark.usefixtures("reset_zone_and_anomaly_state")
async def test_zone_concurrent_atomic_increment(client: AsyncClient) -> None:
    async def post_event(i: int) -> int:
        payload = _payload(
            vehicle_id=f"v-{i + 1}",
            timestamp=f"2026-05-09T12:00:{i:02d}Z",
            zone_entered="charging_bay_1",
        )
        response = await client.post("/telemetry", json=payload)
        return response.status_code

    request_count = 50
    statuses = await asyncio.gather(*[post_event(i) for i in range(request_count)])
    assert all(status == 200 for status in statuses)

    async with AsyncSessionLocal() as session:
        record = await session.get(ZoneCount, "charging_bay_1")
        assert record is not None
        assert record.entry_count == request_count


@pytest.mark.usefixtures("reset_zone_and_anomaly_state")
@pytest.mark.parametrize(
    ("payload", "anomaly_type"),
    [
        (_payload(battery_pct=10), "low_battery"),
        (_payload(status="fault"), "fault_status"),
        (_payload(error_codes=["E-100"]), "error_codes_reported"),
        (_payload(speed_mps=5.5), "excessive_speed"),
    ],
)
async def test_anomaly_rules_create_rows(
    client: AsyncClient,
    payload: dict,
    anomaly_type: str,
) -> None:
    response = await client.post("/telemetry", json=payload)
    assert response.status_code == 200

    event_id = UUID(response.json()["telemetry_event_id"])
    async with AsyncSessionLocal() as session:
        stmt = select(Anomaly).where(Anomaly.telemetry_event_id == event_id)
        anomalies = (await session.execute(stmt)).scalars().all()
        anomaly_types = {anomaly.anomaly_type for anomaly in anomalies}
        assert anomaly_type in anomaly_types


@pytest.mark.usefixtures("reset_zone_and_anomaly_state")
async def test_impossible_position_jump_creates_anomaly(client: AsyncClient) -> None:
    first = await client.post(
        "/telemetry",
        json=_payload(timestamp="2026-05-09T12:00:00Z", lat=37.4100, lon=-122.0800),
    )
    assert first.status_code == 200

    second = await client.post(
        "/telemetry",
        json=_payload(timestamp="2026-05-09T12:00:01Z", lat=37.4200, lon=-122.0800),
    )
    assert second.status_code == 200

    second_event_id = UUID(second.json()["telemetry_event_id"])
    async with AsyncSessionLocal() as session:
        stmt = select(Anomaly).where(Anomaly.telemetry_event_id == second_event_id)
        anomalies = (await session.execute(stmt)).scalars().all()
        anomaly_types = {anomaly.anomaly_type for anomaly in anomalies}
        assert "impossible_position_jump" in anomaly_types


@pytest.mark.usefixtures("reset_zone_and_anomaly_state")
async def test_get_anomalies_filters_and_sorting(client: AsyncClient) -> None:
    r1 = await client.post(
        "/telemetry",
        json=_payload(
            vehicle_id="v-12",
            timestamp="2026-05-09T12:00:00Z",
            battery_pct=10,
        ),
    )
    r2 = await client.post(
        "/telemetry",
        json=_payload(
            vehicle_id="v-13",
            timestamp="2026-05-09T12:00:02Z",
            speed_mps=6.0,
        ),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    all_response = await client.get("/anomalies")
    assert all_response.status_code == 200
    anomalies = all_response.json()
    assert len(anomalies) >= 2
    created_at_values = [item["created_at"] for item in anomalies]
    assert created_at_values == sorted(created_at_values, reverse=True)

    by_vehicle = await client.get("/anomalies", params={"vehicle_id": "v-12"})
    assert by_vehicle.status_code == 200
    assert by_vehicle.json()
    assert all(item["vehicle_id"] == "v-12" for item in by_vehicle.json())

    start_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    by_time = await client.get(
        "/anomalies",
        params={"start_time": start_time, "end_time": end_time},
    )
    assert by_time.status_code == 200
    assert by_time.json()
