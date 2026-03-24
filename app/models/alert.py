import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    min_price_uf: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    max_price_uf: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    target_communes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    min_bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    min_score: Mapped[int] = mapped_column(SmallInteger, default=70)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Alert user={self.user_id} {self.min_price_uf}-{self.max_price_uf}UF>"
