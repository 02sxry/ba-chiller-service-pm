import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _development_secret() -> str:
    return f"generated-development-{secrets.token_urlsafe(32)}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "BA_PMnotification"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = Field(default_factory=_development_secret)
    database_url: str = (
        "mssql+pyodbc://admin:admin@localhost:1433/BA_PMnotification?"
        "driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    )
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
    google_service_account_file: str | None = None
    google_use_real_provider: bool = False
    gemini_api_key: str | None = None
    upload_max_bytes: int = 10 * 1024 * 1024
    slot_warning_months: int = Field(default=2, ge=0, le=12)
    worker_poll_seconds: int = Field(default=5, ge=1, le=300)
    scheduler_interval_seconds: int = Field(default=3600, ge=30, le=86400)
    scheduler_error_retry_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def production_guards(self) -> "Settings":
        if self.app_env == "production" and (
            len(self.secret_key) < 32 or self.secret_key.startswith("generated-development-")
        ):
            raise ValueError("ต้องกำหนด SECRET_KEY อย่างน้อย 32 ตัวอักษรใน production")
        return self

    @property
    def line_allowlist(self) -> set[str]:
        return {value.strip() for value in self.line_destination_allowlist.split(",") if value.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

