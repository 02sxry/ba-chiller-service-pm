import time
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.domain.enums import NotificationStatus
from app.domain.models import NotificationJob
from app.integrations.line import MockLineProvider, build_flex_message

log = structlog.get_logger()


def process_once() -> int:
    settings = get_settings()
    provider = MockLineProvider()
    processed = 0
    with SessionLocal.begin() as db:
        jobs = db.scalars(
            select(NotificationJob)
            .where(NotificationJob.status == NotificationStatus.PENDING, NotificationJob.available_at <= datetime.now(UTC))
            .with_for_update(skip_locked=True)
            .limit(20)
        ).all()
        for job in jobs:
            job.status = NotificationStatus.SENDING
            job.attempts += 1
            if not settings.notifications_enabled or settings.notification_kill_switch:
                job.status = NotificationStatus.REVIEW_REQUIRED
                job.last_error = "การส่ง notification ถูกปิดตามค่าเริ่มต้น"
                continue
            if settings.line_allowlist and job.destination_id not in settings.line_allowlist:
                job.status = NotificationStatus.REVIEW_REQUIRED
                job.last_error = "ปลายทางไม่อยู่ใน allowlist"
                continue
            result = provider.push(job.destination_id, build_flex_message(job.kind, job.payload))
            if result.accepted:
                job.status = NotificationStatus.ACCEPTED
                job.provider_message_id = result.provider_message_id
            else:
                job.status = NotificationStatus.FAILED if job.attempts >= 5 else NotificationStatus.PENDING
                job.last_error = result.error
                job.available_at = datetime.now(UTC) + timedelta(minutes=2 ** job.attempts)
            processed += 1
    return processed


def main() -> None:
    while True:
        try:
            process_once()
        except Exception as exc:
            log.exception("worker_cycle_failed", error_type=type(exc).__name__)
        time.sleep(5)


if __name__ == "__main__":
    main()

