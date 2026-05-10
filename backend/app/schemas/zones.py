from pydantic import BaseModel


class ZoneCountResponse(BaseModel):
    zone_id: str
    entry_count: int
