from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StreamDraft(Base):
    """Состояние потока у нас: рабочие офферы и снимок опубликованного."""

    __tablename__ = "stream_drafts"

    stream_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False
    )
    campaign_id: Mapped[int] = mapped_column(index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    offers: Mapped[list["DraftOffer"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftOffer.position",
    )


class DraftOffer(Base):
    __tablename__ = "draft_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(
        ForeignKey("stream_drafts.stream_id")
    )
    offer_id: Mapped[int]
    share: Mapped[int] = mapped_column(default=0)
    pinned: Mapped[bool] = mapped_column(default=False)
    removed: Mapped[bool] = mapped_column(default=False)
    # Снимок «как в Keitaro после последней публикации».
    # None: такого оффера в Keitaro не было.
    published_share: Mapped[int | None] = mapped_column(default=None)
    published_active: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(default=0)

    draft: Mapped["StreamDraft"] = relationship(back_populates="offers")
