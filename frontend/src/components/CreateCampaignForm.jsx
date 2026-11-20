import { useState } from "react";
import { createCampaign } from "../api";
import Button from "./Button";
import OfferSearch from "./OfferSearch";

export default function CreateCampaignForm({ onCreated }) {
    const [name, setName] = useState("");
    const [geo, setGeo] = useState("");
    const [offer, setOffer] = useState(null);
    const [error, setError] = useState(null);
    const [sending, setSending] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setSending(true);
        setError(null);
        try {
            const campaign = await createCampaign({ name, geo, offer_id: offer.id });
            setName("");
            setGeo("");
            setOffer(null);
            onCreated(campaign);
        } catch (e) {
            setError(e.message);
        } finally {
            setSending(false);
        }
    }

    return (
        <form className="card form" onSubmit={handleSubmit}>
            <h2>Новая кампания</h2>
            <div className="field">
                <label htmlFor="campaign-name">Название</label>
                <input
                    id="campaign-name"
                    className="input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
            </div>
            <div className="field field-narrow">
                <label htmlFor="campaign-geo">Гео</label>
                <input
                    id="campaign-geo"
                    className="input"
                    value={geo}
                    onChange={(e) => setGeo(e.target.value)}
                    maxLength={2}
                    placeholder="DE"
                    required
                />
                <span className="hint">Двухбуквенный код страны</span>
            </div>
            <div className="field">
                <span className="label">Оффер</span>
                {offer ? (
                    <div className="chosen">
                        <span>
                            <span className="picker-id">{offer.id}</span> {offer.name}
                        </span>
                        <Button variant="ghost" onClick={() => setOffer(null)}>
                            Изменить
                        </Button>
                    </div>
                ) : (
                    <OfferSearch onSelect={setOffer} />
                )}
            </div>
            {error && <p className="error">Ошибка: {error}</p>}
            <div className="form-actions">
                <Button
                    type="submit"
                    variant="primary"
                    disabled={sending || offer === null}
                >
                    {sending ? "Создаём…" : "Создать кампанию"}
                </Button>
            </div>
        </form>
    );
}
