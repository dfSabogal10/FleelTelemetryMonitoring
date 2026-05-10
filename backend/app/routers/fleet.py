from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vehicle import Vehicle
from app.schemas.fleet import FleetStateResponse, VehicleSnapshotResponse

router = APIRouter()


@router.get("/fleet/state", response_model=FleetStateResponse)
async def get_fleet_state(db: AsyncSession = Depends(get_db)) -> FleetStateResponse:
    stmt = select(Vehicle.status, func.count()).group_by(Vehicle.status)
    rows = (await db.execute(stmt)).all()
    counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
    for status, count in rows:
        if status in counts:
            counts[status] = int(count)
    return FleetStateResponse(**counts)


@router.get("/vehicles", response_model=list[VehicleSnapshotResponse])
async def get_vehicles(db: AsyncSession = Depends(get_db)) -> list[VehicleSnapshotResponse]:
    stmt = select(Vehicle).order_by(Vehicle.id.asc())
    vehicles = (await db.execute(stmt)).scalars().all()
    return [
        VehicleSnapshotResponse(
            vehicle_id=vehicle.id,
            status=vehicle.status,
            battery_pct=vehicle.battery_pct,
            speed_mps=vehicle.speed_mps,
            lat=vehicle.lat,
            lon=vehicle.lon,
            last_seen_at=vehicle.last_seen_at,
        )
        for vehicle in vehicles
    ]
