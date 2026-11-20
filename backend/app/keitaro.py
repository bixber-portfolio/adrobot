from typing import Any

import httpx

from app.config import settings

DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = "Mozilla/5.0 (compatible; adrobot/1.0)"
# Сколько символов ответа Keitaro показывать в тексте ошибки.
ERROR_BODY_PREVIEW_LENGTH = 300


class KeitaroError(Exception):
    """Keitaro ответил ошибкой (код 4xx или 5xx)."""

    def __init__(self, status_code: int, body: str):
        preview = body[:ERROR_BODY_PREVIEW_LENGTH]
        super().__init__(f"Keitaro вернул {status_code}: {preview}")
        self.status_code = status_code
        self.body = body


class KeitaroClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Api-Key": api_key, "User-Agent": USER_AGENT},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            raise KeitaroError(response.status_code, response.text)
        return response.json() if response.content else None

    def list_offers(self) -> list[dict]:
        return self._request("GET", "/offers")

    def list_campaigns(self) -> list[dict]:
        return self._request("GET", "/campaigns")

    def get_campaign_streams(self, campaign_id: int) -> list[dict]:
        return self._request("GET", f"/campaigns/{campaign_id}/streams")

    def build_report(self, payload: dict) -> dict | None:
        return self._request("POST", "/report/build", json=payload)

    def create_campaign(self, payload: dict) -> dict:
        return self._request("POST", "/campaigns", json=payload)

    def create_stream(self, payload: dict) -> dict:
        return self._request("POST", "/streams", json=payload)

    def update_stream(self, stream_id: int, payload: dict) -> dict | None:
        return self._request("PUT", f"/streams/{stream_id}", json=payload)

    def delete_campaign(self, campaign_id: int) -> None:
        self._request("DELETE", f"/campaigns/{campaign_id}")


def get_keitaro_client() -> KeitaroClient:
    return KeitaroClient(settings.keitaro_api_base, settings.keitaro_api_key)
