from __future__ import annotations

import math
from datetime import UTC
from typing import TypedDict

from app.models.telemetry_event import TelemetryEvent
from app.schemas.telemetry import TelemetryIngestRequest

LOW_BATTERY_THRESHOLD = 15
EXCESSIVE_SPEED_THRESHOLD_MPS = 5.0
IMPOSSIBLE_JUMP_THRESHOLD_MPS = 8.0


class DetectedAnomaly(TypedDict):
    type: str
    severity: str
    message: str


def detect_anomalies(
    payload: TelemetryIngestRequest,
    previous_event: TelemetryEvent | None,
) -> list[DetectedAnomaly]:
    anomalies: list[DetectedAnomaly] = []

    if payload.status.value == "fault":
        anomalies.append(
            {
                "type": "fault_status",
                "severity": "critical",
                "message": f"Vehicle {payload.vehicle_id} reported fault status.",
            }
        )

    if payload.battery_pct < LOW_BATTERY_THRESHOLD:
        anomalies.append(
            {
                "type": "low_battery",
                "severity": "warning",
                "message": (
                    f"Vehicle {payload.vehicle_id} battery is low at {payload.battery_pct}%."
                ),
            }
        )

    if payload.speed_mps > EXCESSIVE_SPEED_THRESHOLD_MPS:
        anomalies.append(
            {
                "type": "excessive_speed",
                "severity": "warning",
                "message": (
                    f"Vehicle {payload.vehicle_id} speed {payload.speed_mps:.2f} m/s exceeds "
                    f"{EXCESSIVE_SPEED_THRESHOLD_MPS:.1f} m/s."
                ),
            }
        )

    if payload.error_codes:
        anomalies.append(
            {
                "type": "error_codes_reported",
                "severity": "warning",
                "message": (
                    f"Vehicle {payload.vehicle_id} reported error codes: "
                    f"{', '.join(payload.error_codes)}."
                ),
            }
        )

    jump_anomaly = _detect_impossible_position_jump(payload, previous_event)
    if jump_anomaly is not None:
        anomalies.append(jump_anomaly)

    return anomalies


def _detect_impossible_position_jump(
    payload: TelemetryIngestRequest,
    previous_event: TelemetryEvent | None,
) -> DetectedAnomaly | None:
    if previous_event is None:
        return None

    previous_timestamp = previous_event.timestamp
    if previous_timestamp.tzinfo is None:
        previous_timestamp = previous_timestamp.replace(tzinfo=UTC)

    elapsed_seconds = (payload.timestamp - previous_timestamp).total_seconds()
    if elapsed_seconds <= 0:
        return None

    distance_m = _haversine_meters(
        previous_event.lat,
        previous_event.lon,
        payload.lat,
        payload.lon,
    )
    implied_speed = distance_m / elapsed_seconds
    if implied_speed <= IMPOSSIBLE_JUMP_THRESHOLD_MPS:
        return None

    return {
        "type": "impossible_position_jump",
        "severity": "warning",
        "message": (
            f"Vehicle {payload.vehicle_id} implied speed {implied_speed:.2f} m/s between "
            f"telemetry events exceeds {IMPOSSIBLE_JUMP_THRESHOLD_MPS:.1f} m/s."
        ),
    }


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


