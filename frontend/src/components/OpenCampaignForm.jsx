import CampaignSearch from "./CampaignSearch";

export default function OpenCampaignForm({ onOpen }) {
    return (
        <section className="card open-form">
            <h2>Найти кампанию</h2>
            <CampaignSearch onSelect={onOpen} />
        </section>
    );
}
