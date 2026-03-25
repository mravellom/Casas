import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RentAverage(Base):
    __tablename__ = "rent_averages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    commune: Mapped[str] = mapped_column(String(100), nullable=False)
    bedrooms: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    avg_rent_uf: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    median_rent_uf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    min_rent_uf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    max_rent_uf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_rent_commune_beds", "commune", "bedrooms", unique=True),
    )

    def __repr__(self) -> str:
        return f"<RentAverage {self.commune} {self.bedrooms}d avg={self.avg_rent_uf}UF/mes>"
