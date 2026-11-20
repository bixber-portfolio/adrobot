import { searchCampaigns } from "../api";
import SearchPicker from "./SearchPicker";

const STATE_LABELS = { disabled: "выключена" };

const campaignKey = (campaign) => campaign.id;

const renderCampaign = (campaign) => (
    <>
        <span className="picker-id">{campaign.id}</span>
        <span className="picker-main">
            <span>{campaign.name || "(без названия)"}</span>
            <span className="picker-sub">
                {campaign.alias}
                {STATE_LABELS[campaign.state] &&
                    ` · ${STATE_LABELS[campaign.state]}`}
            </span>
        </span>
    </>
);

export default function CampaignSearch({ onSelect }) {
    return (
        <SearchPicker
            search={searchCampaigns}
            itemKey={campaignKey}
            renderItem={renderCampaign}
            placeholder="Номер, название или алиас кампании"
            hint="Начните вводить номер, название или алиас кампании"
            showAllLabel="Показать все кампании"
            onSelect={onSelect}
        />
    );
}
