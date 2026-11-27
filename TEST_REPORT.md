# Test Report

## Local UAT — 27 พฤศจิกายน 2026

ทดสอบกับ SQL Server 2022 Developer 16.0.4205.1, ODBC Driver 18 และฐานทดสอบที่ตั้ง compatibility level 110 โดยใช้ข้อมูลจำลอง

| เส้นทางทดสอบ | ผล |
|---|---|
| อัปเกรดฐานเดิมจากก่อนแก้ Unicode | ทำ error 5074 ซ้ำได้ด้วย migration เดิม ฉบับแก้อัปเกรดผ่าน ข้อมูลเดิมและดัชนีอยู่ครบ |
| สร้างฐานว่างแล้วรันถึง Alembic head | ผ่าน และ `alembic check` ไม่พบ schema drift |
| Backend pytest และ Ruff | ผ่าน 64 รายการ และ lint ผ่าน |
| TypeScript และ Vite build | ผ่าน |
| Chromium ผ่าน Dashboard | เข้าสู่ระบบ เพิ่มโรงพยาบาลและสถานที่ภาษาไทย เพิ่ม Chiller โดยเว้นรุ่น สร้างแผน PM และออกจากระบบได้ |
| Chromium ผ่านคิวอนุมัติ | รับ Webhook จำลองจากกลุ่มช่าง แสดงข้อความก่อนส่ง อนุมัตินัด เห็นในปฏิทิน และ Archive แล้วปิดรอบกับยกเลิกนัดที่เกี่ยวข้อง |
| Notification worker | ผ่านการดึงงานจาก SQL Server และส่งด้วย mock provider |

การยืนยันบน SQLEXPRESS 2012 ของผู้ใช้และการเชื่อม LINE จริงยังรอทดสอบ รายละเอียดอัปเกรดฐานเดิมอยู่ใน `docs/SQL_SERVER.md`

วันที่ทดสอบ 23 พฤศจิกายน 2026

## ผลที่ผ่าน

| ชุดทดสอบ | ผล | หลักฐาน |
|---|---:|---|
| Backend business rules/API | pending | ต้องรัน pytest กับ SQL Server/ODBC Driver 18 ของเครื่องปลายทาง |
| Python lint | ผ่าน | Ruff ตรวจ app, tests และ Alembic environment |
| SQL Server migration | ผ่านด้าน schema compile | Alembic ใช้ metadata แบบ SQL Server และต้องทดสอบกับ instance จริง |
| Schema drift | ผ่าน | Alembic check รายงาน `No new upgrade operations detected` |
| Frontend type/build | ผ่าน | TypeScript build และ Vite production bundle |
| API startup | ผ่าน | Uvicorn start สำเร็จ |
| Health endpoint | ผ่าน | database `ok`, LINE/Google `mock`, Gemini/notifications disabled |
| OpenAPI | ผ่าน | HTTP 200, schema 29,311 bytes ณ เวลาทดสอบ |
| Backend Docker image | pending | Python 3.12 + ODBC Driver 18 + uv lockfile |
| Frontend Docker image | ผ่าน | Node 24 build + Nginx runtime, image `BA_PMnotification-frontend:test` |
| Container smoke checks | ผ่าน | Backend import สำเร็จ และ Nginx config syntax ผ่านเมื่อมี Compose service hostname |
| Production Compose config | ผ่าน | `docker compose --env-file .env ... config --quiet` |
| Full Compose cold start | pending | ต้องมี SQL Server reachable ก่อน migration/backend health |
| HTTPS reverse proxy | ผ่าน | HTTP redirect, HTTPS 200, security headers และ `/api/v1/health` ผ่าน Caddy |
| Admin bootstrap/login | ผ่าน | สร้าง Admin แบบ interactive ใน container, รับ bearer token และเรียก protected API HTTP 200 |
| Backup/restore rehearsal | ผ่าน | custom-format dump + SHA-256, restore เข้า isolated database และ counts/ข้อมูลตรงต้นทาง |
| Restore safety guard | ผ่าน | สคริปต์ปฏิเสธ target ที่ไม่ขึ้นต้นด้วย `BA_PMnotification_restore` |
| Database outage recovery | pending | ต้องทดสอบกับ SQL Server จริง; worker/scheduler มี retry handling |
| Scheduler fast retry | ผ่าน | หลัง outage scheduler retry สำเร็จใน 30 วินาที ไม่รอรอบปกติ 1 ชั่วโมง |
| Production secret guard | ผ่าน | production ปฏิเสธ generated development secret และยอมรับ explicit secret ที่ยาวตามเกณฑ์ |
| Webhook relay controls | ผ่าน | wrong path 404, wrong method 403, body เกิน 1 MiB 413 และ burst เกิน limit 429 |
| Webhook HMAC/dedup | ผ่าน | valid signature accepted 1 ครั้ง, duplicate accepted 0 และ invalid signature 401 |
| Relay backend recovery | ผ่าน | relay resolve Docker DNS ใหม่หลัง backend recreate และกลับมาส่งต่อ HTTP 200 |
| Frontend proxy recovery | ผ่าน | recreate backend container แล้ว HTTPS frontend/API กลับ HTTP 200 โดยไม่ recreate frontend |

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
- Public internet/TLS tunnel และ LINE Verify Webhook จริงยังไม่ได้ทดสอบ

Docker build ครั้งแรกใน execution environment ติด proxy CA แบบ self-signed ทั้ง PyPI และ npm registry จากนั้น build ผ่านเมื่อส่ง CA เป็น BuildKit secret; certificate ไม่ถูก copy หรือฝังใน image

ไม่มีการนับรายการที่ไม่ได้รันเป็น test ผ่าน

# รายงานการทดสอบล่าสุด — 23 พฤศจิกายน 2026

## ผลการตรวจหลังเพิ่ม Google production adapter

- SQL Server/ODBC Driver 18: รอทดสอบบนเครื่องปลายทาง
- Ruff: ผ่าน `ruff check app tests alembic --exclude alembic/versions`
- Frontend: ผ่าน `npm ci && npm run build`
- Alembic: migration `upgrade head` ผ่าน
- Google operations retry action: ผ่าน backend regression และ frontend TypeScript/Vite build
- LINE Q&A parser และ bounded reply payload: ผ่าน
- Google Sheets stable row update: ผ่าน provider contract test สำหรับ existing row และไม่เพิ่มข้อมูลซ้ำเมื่อ retry
- Google Drive folder routing: ผ่าน missing-folder safety test
- LINE Messaging API adapter: ผ่าน provider contract tests ด้วย fake HTTP client; ไม่มีการเรียก endpoint จริง
- Gemini adapter: ผ่าน JSON contract/fallback tests ด้วย fake HTTP client; ไม่มีการเรียก endpoint จริง
- Intake AI suggestion: เก็บเป็น review-only ใน `parsed_data.ai_suggestion` และไม่อนุมัติอัตโนมัติ
- Full local Compose: migration สำเร็จ, ทุก service healthy, HTTPS health/login/dashboard ผ่าน HTTP 200
- OpenAPI proxy: `/api/docs` และ `/openapi.json` ส่งถึง backend ได้ถูกต้อง

การทดสอบครั้งนี้ไม่ใช้ Google credentials และไม่มีการส่งข้อมูลออกไปยัง Google Workspace จริง

คู่มือทดลองบนโน้ตบุ๊กถูกเพิ่มใน `docs/LAPTOP_TEST.md` พร้อมคำสั่ง Windows PowerShell และ macOS/Linux

การเปลี่ยน Login เป็น User ID/Password ผ่าน frontend build และ Python compile check แล้ว; integration test ต้องรันกับ SQL Server ของเครื่องปลายทาง

การสร้าง Google Sheets workbook template รอบล่าสุดผ่าน: สร้างไฟล์ `output/BA_PMnotification_MASTER.xlsx` สำเร็จ ตรวจสอบชื่อชีต 17 ชีตและหัวคอลัมน์ของ Input tabs แล้ว; ยังไม่ได้ทดสอบกับ Google credentials จริง

หลังเพิ่มหน้า Admin กรอกข้อมูลฐานข้อมูล: `python -m compileall -q backend/app`, `git diff --check` และ `npm run build` ผ่าน; ยังไม่ได้รัน integration test ที่ต้องใช้ SQL Server จริงในรอบนี้

หลังปรับ local password policy และ Admin repair command: backend compile, `git diff --check` และ frontend build ผ่าน; ยังไม่ได้ทดสอบสิทธิ์กับฐานข้อมูลของผู้ใช้โดยตรง

หลังเพิ่ม User management endpoints และ UI: backend compile, `git diff --check` และ frontend production build ผ่าน; ยังไม่ได้รัน integration test ที่ต้องใช้ SQL Server จริง

## ตรวจการซ่อนโรงพยาบาลที่ปิดใช้งาน — 27 พฤศจิกายน 2026

- หน้าโรงพยาบาลเรียก `/hospitals?active=true` จึงไม่แสดงรายการที่ปิดใช้งานแล้ว
- แยก React Query key ระหว่างรายการ `active` และ `all` ป้องกัน cache จากหน้าประวัติทำให้รายการปิดใช้งานกลับมาแสดง
- `git diff --check` ผ่าน
- `npm run build` ผ่าน TypeScript และ Vite production build

