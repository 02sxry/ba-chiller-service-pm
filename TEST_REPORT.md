# Test Report

วันที่ทดสอบ 23 พฤศจิกายน 2026

## ผลที่ผ่าน

| ชุดทดสอบ | ผล | หลักฐาน |
|---|---:|---|
| Backend business rules/API | 36 passed | pytest กับ PostgreSQL 17 container, 0 failed |
| Python lint | ผ่าน | Ruff ตรวจ app, tests และ Alembic environment |
| PostgreSQL migration | ผ่าน | Alembic upgrade revision `1b6004596e27` |
| Schema drift | ผ่าน | Alembic check รายงาน `No new upgrade operations detected` |
| Frontend type/build | ผ่าน | TypeScript build และ Vite production bundle |
| API startup | ผ่าน | Uvicorn start สำเร็จ |
| Health endpoint | ผ่าน | database `ok`, LINE/Google `mock`, Gemini/notifications disabled |
| OpenAPI | ผ่าน | HTTP 200, schema 29,311 bytes ณ เวลาทดสอบ |
| Backend Docker image | ผ่าน | Python 3.12 + uv lockfile, image `ba-chiller-backend:test` |
| Frontend Docker image | ผ่าน | Node 24 build + Nginx runtime, image `ba-chiller-frontend:test` |
| Container smoke checks | ผ่าน | Backend import สำเร็จ และ Nginx config syntax ผ่านเมื่อมี Compose service hostname |
| Production Compose config | ผ่าน | `docker compose --env-file .env ... config --quiet` |
| Full Compose cold start | ผ่าน | PostgreSQL -> migration/backend health -> frontend/worker/scheduler ตามลำดับ ไม่มี missing-table error |
| HTTPS reverse proxy | ผ่าน | HTTP redirect, HTTPS 200, security headers และ `/api/v1/health` ผ่าน Caddy |
| Admin bootstrap/login | ผ่าน | สร้าง Admin แบบ interactive ใน container, รับ bearer token และเรียก protected API HTTP 200 |
| Backup/restore rehearsal | ผ่าน | custom-format dump + SHA-256, restore เข้า isolated database และ counts/ข้อมูลตรงต้นทาง |
| Restore safety guard | ผ่าน | สคริปต์ปฏิเสธ target ที่ไม่ขึ้นต้นด้วย `ba_chiller_restore` |

## Business rules ที่ทดสอบ

- Automatic frequency 1, 2, 3, 4, 6 และ 12 ครั้งต่อปี
- Start month ที่วนข้ามปีและเรียงเดือนตามปฏิทิน
- Manual months ปฏิเสธเดือนซ้ำ
- Plan approval สร้าง Slots ครบใน transaction และ duplicate yearly plan ถูกปฏิเสธ
- Thai numeric/named date, Buddhist Era และ relative date ใน Asia/Bangkok
- XLSX row validation
- Hospital normalization และ circular month distance
- LINE HMAC signature ถูก/ผิด
- Unknown hospital สร้าง reviewable Draft
- Draft อนุมัติเป็น hospital ใหม่หรือ match พร้อม alias ได้
- Dependent Draft ปฏิเสธการอนุมัติผิดลำดับ และอนุมัติ Hospital -> Equipment -> PM Plan ได้ครบ
- Hospital confirmation เก็บ revision ที่ยืนยัน
- Technician date change สร้าง revision 2, คง Slot และ confirmed revision เดิม
- Duplicate appointment ใน Slot เดิมถูกปฏิเสธ
- Appointment enum ไม่มี `COMPLETED`
- LINE Flex Message มี confirm/reschedule actions ตามชนิด token
- Technician date change ออก token ที่อนุญาตเฉพาะ reschedule
- Google hospital staging import ทำซ้ำได้โดยไม่สร้างซ้ำ
- Google stale version ถูกเก็บเป็น conflict โดยไม่ทับข้อมูลจริง
- Google outbound mock retry ถูกจำกัดจำนวนครั้ง และ duplicate hospital code ถูกเก็บเป็น failed event
- Anonymous ถูกปฏิเสธ, Viewer อ่านได้แต่แก้ master data ไม่ได้ และ Admin สร้างได้
- Admin bootstrap ปฏิเสธอีเมลสงวน/รหัสผ่านสั้น, normalize อีเมล และ hash รหัสผ่าน

## ไม่ผ่านหรือยังรันไม่ได้

- Cloud Desktop เปิด browser ไม่ได้เพราะ browser runtime unavailable
- Playwright ดาวน์โหลด Chromium ไม่ได้เพราะ CDN ตอบ HTTP 403 จึงยังไม่มี visual/E2E browser result
- Real LINE, Google Sheets, Google Drive และ Gemini ไม่ได้ทดสอบเพราะไม่มี credentials และไม่มีสิทธิ์ส่งจริง
- Network outage recovery และ webhook relay ยังไม่ได้ทดสอบ

Docker build ครั้งแรกใน execution environment ติด proxy CA แบบ self-signed ทั้ง PyPI และ npm registry จากนั้น build ผ่านเมื่อส่ง CA เป็น BuildKit secret; certificate ไม่ถูก copy หรือฝังใน image

ไม่มีการนับรายการที่ไม่ได้รันเป็น test ผ่าน

