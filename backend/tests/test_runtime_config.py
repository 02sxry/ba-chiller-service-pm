import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_runtime_retry_intervals_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.worker_poll_seconds == 5
    assert settings.scheduler_interval_seconds == 3600
    assert settings.scheduler_error_retry_seconds == 30


def test_runtime_retry_intervals_reject_busy_loops() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, worker_poll_seconds=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, scheduler_interval_seconds=5)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, scheduler_error_retry_seconds=0)


def test_production_requires_explicit_secret() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, app_env="production")
    settings = Settings(_env_file=None, app_env="production", secret_key="x" * 32)
    assert settings.app_env == "production"
