"""Pydantic request/response schemas (expand as endpoints are added)."""

from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryVehicleStatus,
)

__all__ = [
    "TelemetryIngestRequest",
    "TelemetryIngestResponse",
    "TelemetryVehicleStatus",
]
