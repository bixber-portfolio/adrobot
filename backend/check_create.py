"""Ручная проверка: создаёт в Keitaro настоящую тестовую кампанию.

Запуск из папки backend: python check_create.py
"""
from app.config import settings
from app.keitaro import get_keitaro_client
from app.services.campaigns import create_campaign_with_streams

CAMPAIGN_NAME = "bixber_test_DE"
GEO = "DE"
STREAM_FIELDS = ("position", "name", "schema", "action_type")


def main() -> None:
    client = get_keitaro_client()
    try:
        offer_id = client.list_offers()[0]["id"]
        campaign = create_campaign_with_streams(
            client,
            name=CAMPAIGN_NAME,
            geo=GEO,
            offer_id=offer_id,
            domain_id=settings.keitaro_domain_id,
            group_id=settings.keitaro_group_id,
            traffic_source_id=settings.keitaro_traffic_source_id,
        )
        print("campaign id:", campaign["id"], "alias:", campaign.get("alias"))
        for stream in client.get_campaign_streams(campaign["id"]):
            print(
                *(stream.get(field) for field in STREAM_FIELDS),
                stream.get("action_payload"),
                stream.get("filters"),
                stream.get("offers"),
            )
    finally:
        client.close()


if __name__ == "__main__":
    main()
