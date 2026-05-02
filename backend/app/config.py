from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://bagend:bagend@localhost:5432/bagend"
    port: int = 8001
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    anthropic_api_key: str = ""

    anylist_email: str = ""
    anylist_password: str = ""

    google_calendar_credentials_path: str = ""
    google_calendar_token_path: str = "token.json"
    google_calendar_ids: str = ""

    google_maps_api_key: str = ""
    home_address: str = ""
    brent_work_address: str = ""
    danielle_work_address: str = ""

    trello_api_key: str = ""
    trello_token: str = ""
    trello_board_id: str = ""

    telegram_bot_token: str = ""
    telegram_group_chat_id: str = ""

    weather_lat: float = 40.0196
    weather_lon: float = -75.3135

    pregnancy_safe_expiry: date = date(2026, 10, 15)

    @property
    def pregnancy_safe_active(self) -> bool:
        return date.today() < self.pregnancy_safe_expiry

    @property
    def google_calendar_id_list(self) -> List[str]:
        if not self.google_calendar_ids:
            return []
        return [cid.strip() for cid in self.google_calendar_ids.split(",") if cid.strip()]


settings = Settings()
