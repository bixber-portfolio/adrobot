from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env лежит рядом с папкой app: путь не зависит от того, откуда запущен код.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    keitaro_url: str
    keitaro_api_key: str
    database_url: str = "sqlite:///./adrobot.db"

    keitaro_domain_id: int
    keitaro_group_id: int
    keitaro_traffic_source_id: int
    
    frontend_origin: str = "http://localhost:5173"

    @property
    def keitaro_base_url(self) -> str:
        return self.keitaro_url.rstrip("/")

    @property
    def keitaro_api_base(self) -> str:
        return f"{self.keitaro_base_url}/admin_api/v1"

    def campaign_admin_url(self, campaign_id: int) -> str:
        """Ссылка на кампанию в админке Keitaro."""
        return (
            f"{self.keitaro_base_url}/admin/#!/campaign/{campaign_id}/main"
        )


settings = Settings()
