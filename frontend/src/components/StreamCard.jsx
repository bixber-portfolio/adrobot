import { useState } from "react";
import {
    addOffer,
    cancelStream,
    pushStream,
    removeOffer,
    restoreOffer,
    togglePin,
} from "../api";
import Button from "./Button";
import OfferRow from "./OfferRow";
import OfferSearch from "./OfferSearch";

export default function StreamCard({ stream, onChange }) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState(null);
    const [adding, setAdding] = useState(false);

    async function run(action, doneText = null) {
        setBusy(true);
        setError(null);
        setNotice(null);
        try {
            onChange(await action());
            setNotice(doneText);
        } catch (e) {
            setError(e.message);
        } finally {
            setBusy(false);
        }
    }

    function handleAdd(offer) {
        setAdding(false);
        run(() => addOffer(stream.id, offer.id));
    }

    return (
        <section className={stream.dirty ? "card stream dirty" : "card stream"}>
            <header className="stream-header">
                <div>
                    <h3>{stream.name}</h3>
                    <p className="muted">Кликов сегодня: {stream.clicks_today ?? "н/д"}</p>
                </div>
                <span className={stream.dirty ? "badge badge-warn" : "badge badge-ok"}>
                    {stream.dirty ? "Не опубликовано" : "Опубликовано"}
                </span>
            </header>

            {stream.stream_schema !== "landings" && (
                <p className="muted">
                    Поток пока пустой. После отправки в Keitaro он станет
                    потоком с офферами.
                </p>
            )}

            <div className="table-scroll">
                <table className="offers">
                    <thead>
                        <tr>
                            <th>Оффер</th>
                            <th>Доля</th>
                            <th>Trends</th>
                            <th>Stats</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>
                        {stream.offers.map((offer) => (
                            <OfferRow
                                key={offer.offer_id}
                                offer={offer}
                                busy={busy}
                                onRemove={() => run(() => removeOffer(stream.id, offer.offer_id))}
                                onRestore={() => run(() => restoreOffer(stream.id, offer.offer_id))}
                                onPin={() => run(() => togglePin(stream.id, offer.offer_id))}
                            />
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="add-offer">
                {adding ? (
                    <OfferSearch onSelect={handleAdd} onClose={() => setAdding(false)} />
                ) : (
                    <Button disabled={busy} onClick={() => setAdding(true)}>
                        + Добавить оффер
                    </Button>
                )}
            </div>

            {error && <p className="error">Ошибка: {error}</p>}
            {notice && <p className="notice">{notice}</p>}

            <footer className="stream-footer">
                <Button
                    variant="primary"
                    disabled={busy || !stream.dirty}
                    onClick={() => run(() => pushStream(stream.id), "Изменения отправлены в Keitaro")}
                >
                    Push to KT
                </Button>
                <Button
                    disabled={busy || !stream.dirty}
                    onClick={() => run(() => cancelStream(stream.id), "Изменения отменены")}
                >
                    Cancel
                </Button>
            </footer>
        </section>
    );
}
