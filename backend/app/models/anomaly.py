from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vehicle_id: Mapped[str] = mapped_column(String(64), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    telemetry_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("telemetry_events.id", ondelete="SET NULL"), nullable=True
    )
    anomaly_type: Mapped[str] = mapped_column("type", String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="anomalies")
    telemetry_event: Mapped["TelemetryEvent | None"] = relationship(back_populates="anomalies")
