"""Pydantic request/response schemas (expand as endpoints are added)."""

from app.schemas.anomalies import AnomalyQueryParams, AnomalyResponse
from app.schemas.fleet import FleetStateResponse, VehicleSnapshotResponse
from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryVehicleStatus,
)
from app.schemas.zones import ZoneCountResponse

__all__ = [
    "AnomalyQueryParams",
    "AnomalyResponse",
    "FleetStateResponse",
    "TelemetryIngestRequest",
    "TelemetryIngestResponse",
    "TelemetryVehicleStatus",
    "VehicleSnapshotResponse",
    "ZoneCountResponse",
]
