"""Запуск бэкенда с поддельным Keitaro для ручной проверки интерфейса.

Настоящая логика бэкенда (доли, булавки, черновики, синхронизация) работает
как обычно, а вместо Keitaro отвечает программа в памяти. Данные сбрасываются
при перезапуске, база для черновиков отдельная (fake.db, удаляется сама).

Запуск из папки backend:  python fake_keitaro.py
Бэкенд поднимется на http://localhost:8090 (документация: /docs).
Остановить бэкенд с настоящим Keitaro перед запуском.

Чтобы изобразить правки «руками в Keitaro», в /docs есть раздел fake:
добавить поток в кампанию, включить/выключить/убрать оффер в потоке.
"""
import copy
import os
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "fake.db"
DB_FILE.unlink(missing_ok=True)

# Настройки задаём до импорта приложения: оно читает их при импорте.
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
for name, value in {
    "KEITARO_URL": "https://fake-keitaro.local",
    "KEITARO_API_KEY": "fake",
    "KEITARO_DOMAIN_ID": "1",
    "KEITARO_GROUP_ID": "1",
    "KEITARO_TRAFFIC_SOURCE_ID": "1",
}.items():
    os.environ[name] = value

import uvicorn  # noqa: E402
from fastapi import APIRouter, Depends, HTTPException  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.deps import get_client  # noqa: E402
from app.keitaro import KeitaroError  # noqa: E402
from app.main import app  # noqa: E402

PORT = 8090
FIRST_NEW_ID = 5000
OFFER_NAMES = {
    101: "Casino Royal",
    102: "Nutra Slim",
    103: "Crypto Start",
    104: "Dating Pro",
    105: "Loan Fast",
    106: "Games Hub",
}
DEMO_CAMPAIGN_ID = 1001


class FakeKeitaro:
    def __init__(self) -> None:
        self.offers = [
            {"id": offer_id, "name": name, "state": "active"}
            for offer_id, name in OFFER_NAMES.items()
        ]
        self.campaigns: dict[int, dict] = {}
        self.streams: dict[int, dict] = {}
        self._next_id = FIRST_NEW_ID
        self._seed()

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _seed(self) -> None:
        self.campaigns[DEMO_CAMPAIGN_ID] = {
            "id": DEMO_CAMPAIGN_ID,
            "name": "Demo DE",
            "alias": "demode1",
            "state": "active",
        }
        self.add_stream(
            DEMO_CAMPAIGN_ID,
            "Not DE -> Google",
            "redirect",
            [],
            action_payload="https://www.google.com",
        )
        self.add_stream(
            DEMO_CAMPAIGN_ID, "Offers DE", "landings", [(101, 60), (102, 40)]
        )
        self.campaigns[1002] = {
            "id": 1002,
            "name": "Demo FR",
            "alias": "demofr2",
            "state": "active",
        }
        self.add_stream(1002, "Offers FR", "landings", [(103, 100)])

    def add_stream(
        self,
        campaign_id: int,
        name: str,
        schema: str,
        offers: list[tuple[int, int]],
        action_payload: str = "",
    ) -> dict:
        stream = {
            "id": self._new_id(),
            "campaign_id": campaign_id,
            "name": name,
            "type": "regular",
            "position": len(self._campaign_streams(campaign_id)) + 1,
            "schema": schema,
            "action_payload": action_payload,
            "offers": [
                {"offer_id": offer_id, "share": share, "state": "active"}
                for offer_id, share in offers
            ],
        }
        self.streams[stream["id"]] = stream
        return stream

    def _campaign_streams(self, campaign_id: int) -> list[dict]:
        return [
            s for s in self.streams.values() if s["campaign_id"] == campaign_id
        ]

    # ---- то, что использует бэкенд ----

    def list_offers(self) -> list[dict]:
        return copy.deepcopy(self.offers)

    def list_campaigns(self) -> list[dict]:
        return copy.deepcopy(list(self.campaigns.values()))

    def get_campaign_streams(self, campaign_id: int) -> list[dict]:
        if campaign_id not in self.campaigns:
            raise KeitaroError(404, '{"error":"Not found"}')
        return copy.deepcopy(self._campaign_streams(campaign_id))

    def build_report(self, payload: dict) -> dict:
        campaign_id = payload["filters"][0]["expression"]
        return {
            "rows": [
                {"stream_id": s["id"], "clicks": s["id"] % 17}
                for s in self._campaign_streams(campaign_id)
            ]
        }

    def create_campaign(self, payload: dict) -> dict:
        if any(c["name"] == payload["name"] for c in self.campaigns.values()):
            raise KeitaroError(422, '{"name":["Name is already used"]}')
        campaign_id = self._new_id()
        campaign = {
            "id": campaign_id,
            "name": payload["name"],
            "alias": payload["alias"],
            "state": "active",
        }
        self.campaigns[campaign_id] = campaign
        return copy.deepcopy(campaign)

    def create_stream(self, payload: dict) -> dict:
        if not payload.get("action_type"):
            raise KeitaroError(
                422, '{"action_type":["Action Type is required"]}'
            )
        stream = {**copy.deepcopy(payload), "id": self._new_id()}
        # Настоящий Keitaro сам проставляет оффером состояние «active».
        for offer in stream.get("offers", []):
            offer.setdefault("state", "active")
        self.streams[stream["id"]] = stream
        return copy.deepcopy(stream)

    def update_stream(self, stream_id: int, payload: dict) -> dict:
        stream = self.streams.get(stream_id)
        if stream is None:
            raise KeitaroError(404, '{"error":"Not found"}')
        stream["offers"] = copy.deepcopy(payload["offers"])
        stream["schema"] = payload.get("schema", stream["schema"])
        return copy.deepcopy(stream)

    def delete_campaign(self, campaign_id: int) -> None:
        self.campaigns[campaign_id]["state"] = "deleted"


fake = FakeKeitaro()
router = APIRouter(prefix="/__fake", tags=["fake: правки «руками в Keitaro»"])


@router.post("/campaigns/{campaign_id}/streams")
def add_stream(
    campaign_id: int,
    name: str = "Stream added in Keitaro",
    schema: str = "landings",
    offer_ids: str = "104",
) -> dict:
    """Добавить поток в кампанию. offer_ids: номера через запятую."""
    if campaign_id not in fake.campaigns:
        raise HTTPException(404, "Кампании нет")
    ids = [int(i) for i in offer_ids.split(",") if i.strip()]
    share = 100 // len(ids) if ids else 0
    return fake.add_stream(
        campaign_id, name, schema, [(offer_id, share) for offer_id in ids]
    )


@router.post("/streams/{stream_id}/offers/{offer_id}")
def change_offer(stream_id: int, offer_id: int, state: str = "active") -> dict:
    """state: active, disabled или removed (убрать оффер из потока)."""
    stream = fake.streams.get(stream_id)
    if stream is None:
        raise HTTPException(404, "Потока нет")
    offers = [o for o in stream["offers"] if o["offer_id"] != offer_id]
    if state != "removed":
        share = 0 if state == "disabled" else 10
        offers.append({"offer_id": offer_id, "share": share, "state": state})
    stream["offers"] = offers
    return stream


@router.get("/state")
def show_state() -> dict:
    return {"campaigns": fake.campaigns, "streams": fake.streams}


app.dependency_overrides[get_client] = lambda: fake
app.include_router(router)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    uvicorn.run(app, host="127.0.0.1", port=PORT)
