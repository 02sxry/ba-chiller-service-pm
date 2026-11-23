# Progress

อัปเดตล่าสุด 23 พฤศจิกายน 2026 เวลา Asia/Bangkok

## Milestone ปัจจุบัน

Foundation + core appointment workflow พร้อม PostgreSQL integration tests

## ทำแล้ว

- สร้าง repository แยก `ba-chiller-service-pm` โดยไม่แก้ repository เดิม
- FastAPI app, centralized settings/error handling, CORS และ OpenAPI
- PostgreSQL schema และ Alembic initial migration 26 ตาราง
- Admin/Viewer role, Argon2 password, JWT และ first-Admin bootstrap
- Hospital/Equipment API และ Hospital Draft review/alias matching
- Dependent Draft approval ครบลำดับ Hospital -> Equipment -> PM Plan พร้อมป้องกัน partial approval
- Annual plan preview/approval, automatic/manual months และ atomic PM Slot creation
- Next-year draft generation และ per-plan bulk approval savepoint
- Thai LINE text parser, Buddhist Era/relative dates และ defensive XLSX parser
- Hospital/equipment fuzzy matching และ PM Slot recommendation
- Appointment approval, one appointment per Slot, action tokens, confirmation และ reschedule request
- Technician-initiated confirmed date change โดยคง confirmed revision เดิม
- LINE signature validation, webhook deduplication และ hospital group authorization
- Notification outbox, claim/retry, kill switch และ destination allowlist
- Mock LINE, Google Workspace และ disabled Gemini adapters
- React Thai dashboard, login, hospital form, PM preview และ draft review
- Equipment form, PM plan approval, technician intake queue และ operational appointment tables
- Calendar, confirmation, reschedule และ history routes เชื่อม authoritative appointment API
- Responsive navigation 18 หมวดและ integration health ที่ไม่แสดงสถานะสำเร็จปลอม
- Docker Compose สำหรับ PostgreSQL dev และ local production stack
- Caddy, worker, scheduler, backup/restore, webhook relay และ security docs
- Reproducible Google workbook template generator

## Tests executed

- `pytest -q` กับ PostgreSQL 17 จริง ผ่าน 25 tests
- `ruff check app tests alembic --exclude alembic/versions` ผ่าน
- `alembic upgrade head` ผ่าน
- `alembic check` ผ่านและไม่พบ schema drift
- `npm run build` ผ่าน TypeScript และ Vite production build
- FastAPI start-up, `/api/v1/health` และ `/openapi.json` ผ่าน

## ข้อจำกัดและงานคงเหลือ

- Reports, LINE Groups, Google operations และ Settings บางหน้าเป็น route placeholder
- Google Sheets/Drive production adapters และ reconciliation worker ยังเป็น mock contract
- LINE Flex Message rendering, postback event routing และ natural-language Q&A ต้องต่อจาก provider contract
- Gemini production adapter ยังปิดใช้งาน
- Playwright browser test ยังรันไม่ได้ เพราะ Cloud Desktop ไม่มี browser runtime และ CDN ดาวน์โหลด Chromium ตอบ 403
- Docker production image build, backup restore rehearsal และ outage recovery ยังไม่ได้รัน
- Private GitHub repository พร้อมใช้งานผ่าน GitHub connector แม้ GitHub CLI token ยังใช้ไม่ได้
- ไม่มี credentials จริง จึงไม่ได้ทดสอบหรือส่ง LINE/Google/Gemini จริง

## Next actions

1. เชื่อม Reports UI กับ API
2. ทำ Google import/export adapters, conflict UI และ durable reconciliation
3. ทำ LINE Flex/postback handlers และ deterministic Q&A
4. เพิ่ม API authorization/isolation tests, worker crash/retry tests และ browser E2E
5. ทดสอบ production Compose, backup/restore และ webhook relay ใน isolated environment

## Latest Git commit

Milestone: `core domain, PostgreSQL workflow, Thai dashboard` ตรวจ hash ปัจจุบันด้วย `git rev-parse HEAD`

