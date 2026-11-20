import { searchOffers } from "../api";
import SearchPicker from "./SearchPicker";

const offerKey = (offer) => offer.id;

const renderOffer = (offer) => (
    <>
        <span className="picker-id">{offer.id}</span>
        <span>{offer.name}</span>
    </>
);

export default function OfferSearch({ onSelect, onClose }) {
    return (
        <SearchPicker
            search={searchOffers}
            itemKey={offerKey}
            renderItem={renderOffer}
            placeholder="Номер или название оффера"
            hint="Начните вводить номер или название оффера"
            showAllLabel="Показать все офферы"
            onSelect={onSelect}
            onClose={onClose}
        />
    );
}
