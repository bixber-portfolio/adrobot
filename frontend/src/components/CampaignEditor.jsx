import { useEffect, useState } from "react";
import { getStreams, refreshStreams } from "../api";
import Button from "./Button";
import StaticStreamCard from "./StaticStreamCard";
import StreamCard from "./StreamCard";

export default function CampaignEditor({ campaignId, campaignName }) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        let outdated = false;
        getStreams(campaignId)
            .then((loaded) => {
                if (!outdated) setData(loaded);
            })
            .catch((e) => {
                if (!outdated) setError(e.message);
            });
        return () => {
            outdated = true;
        };
    }, [campaignId]);

    async function handleRefresh() {
        setRefreshing(true);
        setError(null);
        try {
            setData(await refreshStreams(campaignId));
        } catch (e) {
            setError(e.message);
        } finally {
            setRefreshing(false);
        }
    }

    function handleStreamChange(update) {
        setData((current) => ({
            ...current,
            streams: current.streams.map((stream) =>
                stream.id === update.id
                    ? { ...stream, dirty: update.dirty, offers: update.offers }
                    : stream,
            ),
        }));
    }

    if (error) return <p className="error">Ошибка: {error}</p>;
    if (data === null) return <p className="muted">Загрузка…</p>;

    return (
        <div className="editor">
            <div className="editor-header">
                <div>
                    <h2>Кампания {campaignId}</h2>
                    {campaignName && <p className="muted">{campaignName}</p>}
                </div>
                <div className="editor-actions">
                    <a
                        className="btn btn-secondary"
                        href={data.keitaro_url}
                        target="_blank"
                        rel="noreferrer"
                    >
                        View in KT
                    </a>
                    <Button disabled={refreshing} onClick={handleRefresh}>
                        {refreshing ? "Обновляем…" : "Fetch streams from KT"}
                    </Button>
                </div>
            </div>
            {data.streams.length === 0 && (
                <p className="muted">В кампании пока нет потоков.</p>
            )}
            {data.streams.map((stream) =>
                stream.editable ? (
                    <StreamCard
                        key={stream.id}
                        stream={stream}
                        onChange={handleStreamChange}
                    />
                ) : (
                    <StaticStreamCard key={stream.id} stream={stream} />
                ),
            )}
        </div>
    );
}
