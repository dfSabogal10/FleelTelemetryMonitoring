from datetime import datetime

from pydantic import BaseModel


class FleetStateResponse(BaseModel):
    idle: int
    moving: int
    charging: int
    fault: int


class VehicleSnapshotResponse(BaseModel):
    vehicle_id: str
    status: str
    battery_pct: int | None
    speed_mps: float | None
    lat: float | None
    lon: float | None
    last_seen_at: datetime | None
