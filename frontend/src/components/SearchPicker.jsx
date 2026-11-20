import { useEffect, useState } from "react";
import Button from "./Button";

const DEBOUNCE_MS = 300;
const SHORT_LIST = 20;
const FULL_LIST = 500;

export default function SearchPicker({
    search,
    itemKey,
    renderItem,
    placeholder,
    hint,
    showAllLabel,
    onSelect,
    onClose,
}) {
    const [query, setQuery] = useState("");
    const [showAll, setShowAll] = useState(false);
    // Результат помнит, для какого запроса он получен: так видно, что список
    // ещё грузится, и «Ничего не найдено» не мелькает раньше времени.
    const [result, setResult] = useState({ requestKey: null, items: [] });
    const [error, setError] = useState(null);

    // Пока ничего не введено и «показать все» не нажато, на сервер не ходим.
    const active = query.trim() !== "" || showAll;
    const requestKey = `${showAll}:${query}`;
    const loading = result.requestKey !== requestKey && !error;
    const items = result.items;

    useEffect(() => {
        if (!active) return undefined;
        let outdated = false;
        const timer = setTimeout(
            () => {
                search(query, showAll ? FULL_LIST : SHORT_LIST)
                    .then((found) => {
                        if (!outdated) {
                            setResult({ requestKey, items: found });
                            setError(null);
                        }
                    })
                    .catch((e) => {
                        if (!outdated) setError(e.message);
                    });
            },
            showAll ? 0 : DEBOUNCE_MS,
        );
        return () => {
            outdated = true;
            clearTimeout(timer);
        };
    }, [search, query, showAll, active, requestKey]);

    function handleType(event) {
        setQuery(event.target.value);
        setShowAll(false);
    }

    function handleShowAll() {
        setQuery("");
        setShowAll(true);
    }

    function handleSelect(item) {
        setQuery("");
        setShowAll(false);
        setResult({ requestKey: null, items: [] });
        onSelect(item);
    }

    return (
        <div className="picker">
            <input
                className="input"
                value={query}
                onChange={handleType}
                placeholder={placeholder}
            />
            {error && <p className="error">Ошибка поиска: {error}</p>}
            {active ? (
                <ul className="picker-list">
                    {items.map((item) => (
                        <li key={itemKey(item)}>
                            <button
                                type="button"
                                className="picker-item"
                                onClick={() => handleSelect(item)}
                            >
                                {renderItem(item)}
                            </button>
                        </li>
                    ))}
                    {loading && items.length === 0 && (
                        <li className="picker-empty">Загрузка…</li>
                    )}
                    {!loading && items.length === 0 && !error && (
                        <li className="picker-empty">Ничего не найдено</li>
                    )}
                </ul>
            ) : (
                <p className="hint">{hint}</p>
            )}
            <div className="picker-footer">
                {!showAll ? (
                    <Button variant="ghost" onClick={handleShowAll}>
                        {showAllLabel}
                    </Button>
                ) : (
                    <span />
                )}
                {onClose && (
                    <Button variant="ghost" onClick={onClose}>
                        Закрыть
                    </Button>
                )}
            </div>
        </div>
    );
}
