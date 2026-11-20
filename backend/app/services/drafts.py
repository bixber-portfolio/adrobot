from sqlalchemy.orm import Session

from app.models import DraftOffer, StreamDraft, utcnow
from app.services.shares import OfferShare
from app.services.snapshots import PublishedOffer
from app.services.streams import StreamState


def load_state(db: Session, stream_id: int) -> StreamState | None:
    """(рабочий список, снимок опубликованного) потока.

    None, если поток у нас не сохранён.
    """
    draft = db.get(StreamDraft, stream_id)
    if draft is None:
        return None
    working = [
        OfferShare(o.offer_id, o.share, o.pinned, o.removed)
        for o in draft.offers
    ]
    published = [
        PublishedOffer(o.offer_id, o.published_share, o.published_active)
        for o in draft.offers
        if o.published_share is not None
    ]
    return working, published


def _draft_offer(
    offer: OfferShare, snapshot: PublishedOffer | None, position: int
) -> DraftOffer:
    return DraftOffer(
        offer_id=offer.offer_id,
        share=offer.share,
        pinned=offer.pinned,
        removed=offer.removed,
        published_share=snapshot.share if snapshot else None,
        published_active=snapshot.active if snapshot else False,
        position=position,
    )


def save_state(
    db: Session,
    stream_id: int,
    campaign_id: int,
    working: list[OfferShare],
    published: list[PublishedOffer],
) -> None:
    """Перезаписывает состояние потока целиком.

    Старые строки удаляет каскад delete-orphan.
    """
    by_id = {p.offer_id: p for p in published}
    draft = db.get(StreamDraft, stream_id)
    if draft is None:
        draft = StreamDraft(stream_id=stream_id, campaign_id=campaign_id)
        db.add(draft)
    rows = [
        _draft_offer(offer, by_id.get(offer.offer_id), position)
        for position, offer in enumerate(working)
    ]
    # Сначала убираем старые строки и сразу отправляем DELETE в базу:
    # иначе SQLAlchemy вставит новые раньше, чем удалит старые,
    # и сработает UNIQUE(stream_id, offer_id).
    draft.offers.clear()
    db.flush()
    draft.offers = rows
    # Меняются только дочерние строки, сам onupdate у потока не сработает.
    draft.updated_at = utcnow()
    db.commit()


def get_campaign_id(db: Session, stream_id: int) -> int | None:
    draft = db.get(StreamDraft, stream_id)
    return None if draft is None else draft.campaign_id
