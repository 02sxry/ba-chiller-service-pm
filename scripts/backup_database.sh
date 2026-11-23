#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
timestamp=$(date +%Y%m%d_%H%M%S)
backup_path=${1:-"${repo_root}/backups/ba_chiller_${timestamp}.dump"}
backup_dir=$(dirname "${backup_path}")
backup_name=$(basename "${backup_path}")

mkdir -p "${backup_dir}"
if [[ -e "${backup_path}" ]]; then
  echo "ปฏิเสธการเขียนทับไฟล์เดิม: ${backup_path}" >&2
  exit 1
fi

umask 077
docker compose --env-file "${repo_root}/.env" -f "${repo_root}/deploy/local/compose.yaml" \
  exec -T db pg_dump -U ba_chiller -d ba_chiller -Fc > "${backup_path}"

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
