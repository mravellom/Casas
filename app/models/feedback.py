import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False
    )

    # 1=buena oportunidad, 0=mala/falso positivo
    is_good: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_feedback_user_prop", "user_id", "property_id", unique=True),
    )

    @validates("comment")
    def sanitize_comment(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"<[^>]+>", "", value)[:1000]

    def __repr__(self) -> str:
        quality = "buena" if self.is_good else "mala"
        return f"<Feedback user={self.user_id} prop={self.property_id} {quality}>"
