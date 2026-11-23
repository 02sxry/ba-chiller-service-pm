#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 1 ]]; then
  echo "วิธีใช้: $0 <backup.dump> [ba_chiller_restore]" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
backup_path=$1
restore_db=${2:-ba_chiller_restore}

if [[ ! -s "${backup_path}" ]]; then
  echo "ไม่พบไฟล์ backup หรือไฟล์ว่าง: ${backup_path}" >&2
  exit 1
fi
case "${restore_db}" in
  ba_chiller_restore | ba_chiller_restore_*) ;;
  *)
    echo "ชื่อฐาน rehearsal ต้องเป็น ba_chiller_restore หรือขึ้นต้นด้วย ba_chiller_restore_" >&2
    exit 1
    ;;
esac

compose=(docker compose --env-file "${repo_root}/.env" -f "${repo_root}/deploy/local/compose.yaml")
"${compose[@]}" exec -T db dropdb -U ba_chiller --if-exists "${restore_db}"
"${compose[@]}" exec -T db createdb -U ba_chiller "${restore_db}"
"${compose[@]}" exec -T db pg_restore -U ba_chiller --no-owner --exit-on-error \
  --dbname="${restore_db}" < "${backup_path}"
"${compose[@]}" exec -T db psql -U ba_chiller -d "${restore_db}" -Atc \
  "select 'hospitals', count(*) from hospitals
   union all select 'equipment', count(*) from equipment
   union all select 'annual_plans', count(*) from annual_plans
   union all select 'pm_slots', count(*) from pm_slots
   union all select 'appointments', count(*) from appointments
   union all select 'appointment_revisions', count(*) from appointment_revisions
   union all select 'notification_jobs', count(*) from notification_jobs
   union all select 'audit_logs', count(*) from audit_logs
   order by 1;"
echo "Restore rehearsal สำเร็จ: ${restore_db}"
