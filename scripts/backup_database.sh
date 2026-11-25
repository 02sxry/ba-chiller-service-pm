#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
timestamp=$(date +%Y%m%d_%H%M%S)
backup_path=${1:-"${repo_root}/backups/BA_PMnotification_${timestamp}.dump"}
backup_dir=$(dirname "${backup_path}")
backup_name=$(basename "${backup_path}")

mkdir -p "${backup_dir}"
if [[ -e "${backup_path}" ]]; then
  echo "ปฏิเสธการเขียนทับไฟล์เดิม: ${backup_path}" >&2
  exit 1
fi

umask 077
: "${SQLSERVER_HOST:?ตั้งค่า SQLSERVER_HOST ก่อน backup}"
: "${SQLSERVER_DATABASE:=BA_PMnotification}"
: "${SQLSERVER_BACKUP_PATH:?ตั้งค่า SQLSERVER_BACKUP_PATH เป็น path ที่ SQL Server เขียนได้}"

sqlserver_endpoint="${SQLSERVER_HOST}${SQLSERVER_PORT:+,${SQLSERVER_PORT}}"
sqlcmd_args=(-S "${sqlserver_endpoint}" -b -Q "BACKUP DATABASE [${SQLSERVER_DATABASE}] TO DISK = N'${SQLSERVER_BACKUP_PATH}' WITH INIT, COMPRESSION;")
if [[ -n "${SQLSERVER_USER:-}" ]]; then
  sqlcmd_args+=(-U "${SQLSERVER_USER}" -P "${SQLSERVER_PASSWORD:?ตั้งค่า SQLSERVER_PASSWORD เมื่อใช้ SQL Authentication}")
fi
sqlcmd "${sqlcmd_args[@]}"

if [[ ! -s "${backup_path}" ]]; then
  echo "ไฟล์ backup ว่าง" >&2
  exit 1
fi

(
  cd "${backup_dir}"
  sha256sum "${backup_name}" > "${backup_name}.sha256"
)
echo "สร้าง backup: ${backup_path}"
echo "Checksum: ${backup_path}.sha256"
