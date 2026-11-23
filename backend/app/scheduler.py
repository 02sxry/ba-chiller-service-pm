import time
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.planning import generate_next_year_drafts

log = structlog.get_logger()


def run_scheduled_tasks() -> None:
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    if now.month >= 11:
        with SessionLocal.begin() as db:
            drafts = generate_next_year_drafts(db, now.year, now.year + 1)
            log.info("next_year_drafts_checked", count=len(drafts), target_year=now.year + 1)


def main() -> None:
    settings = get_settings()
    while True:
        sleep_seconds = settings.scheduler_interval_seconds
        try:
            run_scheduled_tasks()
        except Exception as exc:
            log.exception("scheduler_cycle_failed", error_type=type(exc).__name__)
            sleep_seconds = settings.scheduler_error_retry_seconds
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()

