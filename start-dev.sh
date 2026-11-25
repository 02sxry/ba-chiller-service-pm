#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
UPDATE_INTERVAL_SECONDS=${UPDATE_INTERVAL_SECONDS:-60}
AUTO_UPDATE=true

if [[ "${1:-}" == "--no-watch" ]]; then
  AUTO_UPDATE=false
fi

log() {
  printf '[BA_PMnotification] %s\n' "$*"
}

find_python() {
  if [[ -x "${ROOT_DIR}/backend/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "${ROOT_DIR}/backend/.venv/Scripts/python.exe"
  elif [[ -x "${ROOT_DIR}/backend/.venv/bin/python" ]]; then
    printf '%s\n' "${ROOT_DIR}/backend/.venv/bin/python"
  else
    return 1
  fi
}

ensure_python() {
  if find_python >/dev/null; then
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    log 'กำลังสร้าง Python virtual environment'
    uv venv "${ROOT_DIR}/backend/.venv"
  elif command -v python >/dev/null 2>&1; then
    log 'กำลังสร้าง Python virtual environment'
    python -m venv "${ROOT_DIR}/backend/.venv"
  else
    log 'ไม่พบ Python หรือ uv กรุณาติดตั้ง Python 3.12+ ก่อน'
    exit 1
  fi
}

ensure_python
PYTHON=$(find_python)

if ! command -v git >/dev/null 2>&1; then
  log 'ไม่พบ Git'
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  log 'ไม่พบ Node.js/npm'
  exit 1
fi
if [[ ! -f "${ROOT_DIR}/backend/.env" ]]; then
  log 'ไม่พบ backend/.env กรุณาตั้งค่า DATABASE_URL ก่อน'
  exit 1
fi

update_dependencies() {
  if command -v uv >/dev/null 2>&1; then
    log 'อัปเดต Backend dependencies'
    UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/ba-pmnotification-uv-cache}" \
      uv sync --frozen --project "${ROOT_DIR}/backend" --extra dev
  else
    log 'อัปเดต Backend dependencies ผ่าน pip'
    "${PYTHON}" -m pip install -e "${ROOT_DIR}/backend"
  fi

  log 'อัปเดต Frontend dependencies'
  (cd "${ROOT_DIR}/frontend" && npm ci)
}

run_migrations() {
  log 'ตรวจสอบและอัปเดต SQL Server schema'
  (cd "${ROOT_DIR}/backend" && "${PYTHON}" -m alembic upgrade head)
}

pull_latest() {
  if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
    log 'มีไฟล์แก้ไขในเครื่อง จึงข้าม git pull เพื่อป้องกันการทับไฟล์'
    return 0
  fi
  log 'ตรวจสอบไฟล์ล่าสุดจาก GitHub'
  git -C "${ROOT_DIR}" pull --ff-only origin main
}

pull_latest
update_dependencies
run_migrations

BACKEND_PID=''
FRONTEND_PID=''
UPDATE_PID=''

cleanup() {
  trap - INT TERM EXIT
  for pid in "${UPDATE_PID}" "${BACKEND_PID}" "${FRONTEND_PID}"; do
    if [[ -n "${pid}" ]]; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}

trap cleanup INT TERM EXIT

log 'กำลังเปิด Backend ที่ http://127.0.0.1:8000'
(
  cd "${ROOT_DIR}/backend"
  exec "${PYTHON}" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

log 'กำลังเปิด Frontend ที่ http://127.0.0.1:5173'
(
  cd "${ROOT_DIR}/frontend"
  exec npm run dev -- --host 127.0.0.1
) &
FRONTEND_PID=$!

auto_update_loop() {
  while sleep "${UPDATE_INTERVAL_SECONDS}"; do
    if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
      log 'พบ local changes จึงยังไม่ดึงไฟล์จาก GitHub'
      continue
    fi
    if ! git -C "${ROOT_DIR}" fetch origin main; then
      log 'ตรวจ GitHub ไม่สำเร็จ จะลองใหม่รอบถัดไป'
      continue
    fi
    current_commit=$(git -C "${ROOT_DIR}" rev-parse HEAD)
    remote_commit=$(git -C "${ROOT_DIR}" rev-parse origin/main)
    if [[ "${current_commit}" == "${remote_commit}" ]]; then
      continue
    fi
    log 'พบการเปลี่ยนแปลงใหม่ กำลังอัปเดตไฟล์และ schema'
    if git -C "${ROOT_DIR}" pull --ff-only origin main; then
      update_dependencies || log 'อัปเดต dependencies ไม่สำเร็จ กรุณาตรวจข้อความด้านบน'
      run_migrations || log 'migration ไม่สำเร็จ กรุณาตรวจ DATABASE_URL และ SQL Server'
    else
      log 'ดึงไฟล์ใหม่ไม่สำเร็จ จะไม่ทับไฟล์ในเครื่อง'
    fi
  done
}

if [[ "${AUTO_UPDATE}" == true ]]; then
  auto_update_loop &
  UPDATE_PID=$!
  log "เปิด auto-update ทุก ${UPDATE_INTERVAL_SECONDS} วินาทีแล้ว"
else
  log 'โหมดไม่ตรวจ GitHub อัตโนมัติ'
fi

log 'ระบบพร้อมใช้งาน กด Ctrl+C เพื่อปิดทั้งหมด'
wait
