from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AnomalyResponse(BaseModel):
    id: UUID
    vehicle_id: str
    type: str
    severity: str
    message: str
    created_at: datetime


class AnomalyQueryParams(BaseModel):
    vehicle_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
