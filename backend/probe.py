"""Разведка тестового Keitaro: только читает справочники, ничего не меняет.

Запуск:
    export KEITARO_URL=https://ВАШ-ТЕСТОВЫЙ-ДОМЕН   # без слэша в конце
    export KEITARO_API_KEY=ваш_ключ                   # ключ никому не давать
    python3 probe.py
"""
import json
import os
import sys
import urllib.request

REQUEST_TIMEOUT_SECONDS = 30
OFFERS_PREVIEW_COUNT = 5
REQUIRED_VARIABLES = ("KEITARO_URL", "KEITARO_API_KEY")


def get(path: str):
    base = os.environ["KEITARO_URL"].rstrip("/")
    request = urllib.request.Request(
        f"{base}/admin_api/v1{path}",
        headers={"Api-Key": os.environ["KEITARO_API_KEY"]},
    )
    with urllib.request.urlopen(
        request, timeout=REQUEST_TIMEOUT_SECONDS
    ) as response:
        return json.load(response)


def main() -> None:
    for name in REQUIRED_VARIABLES:
        if name not in os.environ:
            sys.exit(f"Не задана переменная окружения {name}")

    print("== Фильтры потока, в названии есть country ==")
    for item in get("/stream_filters"):
        if "country" in item["value"].lower():
            print(
                item["value"], item.get("tooltip"), item.get("modes"),
                sep=" | ",
            )

    print("\n== Действия потока (action_type) ==")
    for item in get("/streams_actions"):
        print(
            item.get("key"),
            item.get("name"),
            f"поле: {item.get('field')}",
            f"тип: {item.get('type')}",
            sep=" | ",
        )

    print("\n== Домены (id, имя, состояние) ==")
    for item in get("/domains"):
        print(item["id"], item["name"], item.get("state"))

    print("\n== Группы кампаний (id, имя, тип) ==")
    for item in get("/groups"):
        print(item["id"], item["name"], item.get("type"))

    print("\n== Источники трафика (id, имя) ==")
    for item in get("/traffic_sources"):
        print(item["id"], item["name"])

    offers = get("/offers")
    print(
        f"\n== Офферов всего: {len(offers)}; "
        f"первые {OFFERS_PREVIEW_COUNT} (id, имя, состояние) =="
    )
    for item in offers[:OFFERS_PREVIEW_COUNT]:
        print(item["id"], item["name"], item.get("state"))


if __name__ == "__main__":
    main()
