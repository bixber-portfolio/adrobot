import { useEffect, useState } from "react";
import Button from "./components/Button";
import CampaignEditor from "./components/CampaignEditor";
import CreateCampaignForm from "./components/CreateCampaignForm";
import OpenCampaignForm from "./components/OpenCampaignForm";

const PAGE_CREATE = "create";
const PAGE_EDITOR = "editor";

const STORAGE_KEY = "adrobot.session";

function loadSession() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (saved?.page === PAGE_CREATE || saved?.page === PAGE_EDITOR) {
            const valid = Number.isInteger(saved.campaign?.id);
            return { page: saved.page, campaign: valid ? saved.campaign : null };
        }
    } catch {
        // Хранилище недоступно или данные битые: начинаем с чистого листа.
    }
    return { page: PAGE_EDITOR, campaign: null };
}

export default function App() {
    const [session] = useState(loadSession);
    const [page, setPage] = useState(session.page);
    const [campaign, setCampaign] = useState(session.campaign);
    const [openCount, setOpenCount] = useState(0);
    const [created, setCreated] = useState(null);

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({ page, campaign }));
        } catch {
            // Без хранилища редактор просто не запомнит кампанию.
        }
    }, [page, campaign]);

    function openInEditor(selected) {
        setCampaign({ id: selected.id, name: selected.name });
        // Новое значение ключа заново загружает кампанию, даже если открыта та же.
        setOpenCount((count) => count + 1);
        setPage(PAGE_EDITOR);
    }

    return (
        <>
            <header className="topbar">
                <div className="container topbar-inner">
                    <span className="brand">Adrobot</span>
                    <nav className="tabs">
                        <button
                            type="button"
                            className="tab"
                            aria-current={page === PAGE_CREATE}
                            onClick={() => setPage(PAGE_CREATE)}
                        >
                            Новая кампания
                        </button>
                        <button
                            type="button"
                            className="tab"
                            aria-current={page === PAGE_EDITOR}
                            onClick={() => setPage(PAGE_EDITOR)}
                        >
                            Редактор кампании
                        </button>
                    </nav>
                </div>
            </header>

            <main className="container">
                {page === PAGE_CREATE ? (
                    <>
                        <CreateCampaignForm onCreated={setCreated} />
                        {created && (
                            <div className="card success">
                                <p>
                                    Кампания <strong>{created.id}</strong> «
                                    {created.name}» создана.
                                </p>
                                <Button
                                    variant="primary"
                                    onClick={() => openInEditor(created)}
                                >
                                    Открыть в редакторе
                                </Button>
                            </div>
                        )}
                    </>
                ) : (
                    <>
                        <OpenCampaignForm onOpen={openInEditor} />
                        {campaign === null ? (
                            <p className="muted">
                                Найдите кампанию по номеру, названию или
                                алиасу, чтобы открыть её.
                            </p>
                        ) : (
                            <CampaignEditor
                                key={`${campaign.id}-${openCount}`}
                                campaignId={campaign.id}
                                campaignName={campaign.name}
                            />
                        )}
                    </>
                )}
            </main>
        </>
    );
}
