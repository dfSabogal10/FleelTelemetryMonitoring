from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.constants.zones import ZONES


class TelemetryVehicleStatus(str, Enum):
    idle = "idle"
    moving = "moving"
    charging = "charging"
    fault = "fault"


class TelemetryIngestRequest(BaseModel):
    vehicle_id: str = Field(..., min_length=1)
    timestamp: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    battery_pct: int = Field(..., ge=0, le=100)
    speed_mps: float = Field(..., ge=0)
    status: TelemetryVehicleStatus
    error_codes: list[str]
    zone_entered: str | None = None

    @field_validator("zone_entered")
    @classmethod
    def zone_must_be_known_or_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in ZONES:
            raise ValueError(f"zone_entered must be null or one of the configured zones; unknown zone {value!r}")
        return value


class TelemetryIngestResponse(BaseModel):
    accepted: bool = True
    telemetry_event_id: UUID
