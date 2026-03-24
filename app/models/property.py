import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Precios
    price_uf: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_clp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_m2_uf: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Superficie
    m2_total: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    m2_util: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Características
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    floor: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    has_parking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_bodega: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    building_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Ubicación
    commune: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Imágenes y datos crudos
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Oportunidad
    is_opportunity: Mapped[bool] = mapped_column(Boolean, default=False)
    opportunity_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    has_urgency_keyword: Mapped[bool] = mapped_column(Boolean, default=False)

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_properties_source_id", "source", "source_id", unique=True),
        Index("idx_properties_commune", "commune"),
        Index("idx_properties_price_uf", "price_uf"),
        Index(
            "idx_properties_opportunity",
            "is_opportunity",
            postgresql_where=(is_opportunity == True),  # noqa: E712
        ),
        Index(
            "idx_properties_active",
            "is_active",
            postgresql_where=(is_active == True),  # noqa: E712
        ),
    )

    def __repr__(self) -> str:
        return f"<Property {self.source}:{self.source_id} {self.commune} {self.price_uf}UF>"
