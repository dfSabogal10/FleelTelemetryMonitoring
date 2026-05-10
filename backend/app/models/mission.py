from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vehicle_id: Mapped[str] = mapped_column(String(64), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="missions")
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(back_populates="mission")
