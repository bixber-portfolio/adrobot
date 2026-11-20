export default function StaticStreamCard({ stream }) {
    return (
        <section className="card stream">
            <header className="stream-header">
                <div>
                    <h3>{stream.name}</h3>
                    <p className="muted">
                        Кликов сегодня: {stream.clicks_today ?? "н/д"}
                    </p>
                </div>
                <span className="badge badge-muted">
                    {stream.stream_schema || "поток"}
                </span>
            </header>
            <p className="muted">
                В потоке этого типа нет офферов, поэтому редактор его только
                показывает. Менять такой поток можно в самом Keitaro.
            </p>
        </section>
    );
}
