"""Regression tests for consistent JSON error bodies."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.telemetry import TelemetryService


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


async def test_unknown_zone_validation_returns_422_detail(client: AsyncClient) -> None:
    response = await client.post(
        "/telemetry",
        json=_valid_payload(zone_entered="not_a_real_zone"),
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


async def test_unexpected_server_error_returns_safe_json(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(TelemetryService, "ingest_event", staticmethod(boom))

    response = await client.post("/telemetry", json=_valid_payload())
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Unexpected server error",
        }
    }
