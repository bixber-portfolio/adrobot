import Button from "./Button";

export default function OfferRow({ offer, busy, onRemove, onRestore, onPin }) {
    return (
        <tr className={offer.removed ? "offer-row removed" : "offer-row"}>
            <td data-label="Оффер">
                <span className="picker-id">{offer.offer_id}</span>{" "}
                {offer.name ?? "(без названия)"}
                {(offer.pinned || offer.removed) && (
                    <div className="offer-badges">
                        {offer.pinned && <span className="badge badge-pin">закреплён</span>}
                        {offer.removed && <span className="badge badge-muted">удалён</span>}
                    </div>
                )}
            </td>
            <td data-label="Доля">
                <div className="share">
                    <div className="share-track">
                        <div className="share-bar" style={{ width: `${offer.share}%` }} />
                    </div>
                    <span className="share-value">{offer.share}%</span>
                </div>
            </td>
            <td className="empty-cell" data-label="Trends">—</td>
            <td className="empty-cell" data-label="Stats">—</td>
            <td>
                <div className="row-actions">
                    {offer.removed ? (
                        <Button disabled={busy} onClick={onRestore}>
                            Вернуть
                        </Button>
                    ) : (
                        <>
                            <Button disabled={busy} onClick={onPin} aria-pressed={offer.pinned}>
                                {offer.pinned ? "Открепить" : "Закрепить"}
                            </Button>
                            <Button variant="danger" disabled={busy} onClick={onRemove}>
                                Удалить
                            </Button>
                        </>
                    )}
                </div>
            </td>
        </tr>
    );
}
