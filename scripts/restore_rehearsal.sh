#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 1 ]]; then
  echo "วิธีใช้: $0 <backup.dump> [BA_PMnotification_restore]" >&2
  exit 2
fi

backup_path=$1
restore_db=${2:-BA_PMnotification_restore}

if [[ ! -s "${backup_path}" ]]; then
  echo "ไม่พบไฟล์ backup หรือไฟล์ว่าง: ${backup_path}" >&2
  exit 1
fi
case "${restore_db}" in
  BA_PMnotification_restore | BA_PMnotification_restore_*) ;;
  *)
    echo "ชื่อฐาน rehearsal ต้องเป็น BA_PMnotification_restore หรือขึ้นต้นด้วย BA_PMnotification_restore_" >&2
    exit 1
    ;;
esac

: "${SQLSERVER_HOST:?ตั้งค่า SQLSERVER_HOST ก่อน restore}"

sqlserver_endpoint="${SQLSERVER_HOST}${SQLSERVER_PORT:+,${SQLSERVER_PORT}}"
sqlcmd_args=(-S "${sqlserver_endpoint}" -b -Q "IF DB_ID(N'${restore_db}') IS NOT NULL BEGIN ALTER DATABASE [${restore_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; END; RESTORE DATABASE [${restore_db}] FROM DISK = N'${backup_path}' WITH REPLACE; ALTER DATABASE [${restore_db}] SET MULTI_USER;")
if [[ -n "${SQLSERVER_USER:-}" ]]; then
  sqlcmd_args+=(-U "${SQLSERVER_USER}" -P "${SQLSERVER_PASSWORD:?ตั้งค่า SQLSERVER_PASSWORD เมื่อใช้ SQL Authentication}")
fi
sqlcmd "${sqlcmd_args[@]}"
echo "Restore rehearsal สำเร็จ: ${restore_db}"
