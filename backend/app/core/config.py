from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "BA Chiller Service & PM Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "development-only-secret-change-before-production"
    database_url: str = "postgresql+psycopg://ba_chiller:ba_chiller@localhost:5432/ba_chiller"
    frontend_origin: str = "http://localhost:5173"
    timezone: str = "Asia/Bangkok"
    access_token_minutes: int = 480
    notifications_enabled: bool = False
    notification_kill_switch: bool = True
    line_channel_secret: str | None = None
    line_channel_access_token: str | None = None
    line_destination_allowlist: str = ""
    google_spreadsheet_id: str | None = None
    google_drive_root_folder_id: str | None = None
    gemini_api_key: str | None = None
    upload_max_bytes: int = 10 * 1024 * 1024
    slot_warning_months: int = Field(default=2, ge=0, le=12)

    @model_validator(mode="after")
    def production_guards(self) -> "Settings":
        if self.app_env == "production" and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY ต้องมีอย่างน้อย 32 ตัวอักษรใน production")
        return self

    @property
    def line_allowlist(self) -> set[str]:
        return {value.strip() for value in self.line_destination_allowlist.split(",") if value.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

