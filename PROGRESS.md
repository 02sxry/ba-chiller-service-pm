# Progress

อัปเดตล่าสุด 23 พฤศจิกายน 2026 เวลา Asia/Bangkok

## Milestone ปัจจุบัน

Operational integration milestone: LINE actions, Google staging sync และ container build

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
- LINE Flex Message สำหรับยืนยัน/ขอเลื่อนนัด และ postback routing แบบใช้ action token
- LINE Group mapping API พร้อม validation และ audit log
- Notification outbox, claim/retry, kill switch และ destination allowlist
- Mock LINE, Google Workspace และ disabled Gemini adapters
- React Thai dashboard, login, hospital form, PM preview และ draft review
- Equipment form, PM plan approval, technician intake queue และ operational appointment tables
- Calendar, confirmation, reschedule และ history routes เชื่อม authoritative appointment API
- Google hospital staging sync แบบ idempotent, optimistic version conflict และ durable retry event
- Reports, LINE Groups, Google operations และ Settings operational pages
- Responsive navigation 18 หมวดและ integration health ที่ไม่แสดงสถานะสำเร็จปลอม
- Docker Compose สำหรับ PostgreSQL dev และ local production stack
- Caddy, worker, scheduler, backup/restore, webhook relay และ security docs
- Reproducible Google workbook template generator
- Reproducible backend image จาก `uv.lock`, Docker build secrets สำหรับ private CA และ build-context exclusions
- Production Compose cold start รอ database migration/backend health ก่อนเริ่ม worker และ scheduler
- Caddy รับ `APP_HOST` และข้าม corporate proxy สำหรับ internal service names
- Interactive Admin bootstrap CLI ภายใน backend container พร้อม email/password validation
- Worker/scheduler interval guards และ scheduler fast retry หลัง database outage

## Tests executed

- `pytest -q` กับ PostgreSQL 17 จริง ผ่าน 39 tests
- `ruff check app tests alembic --exclude alembic/versions` ผ่าน
- `alembic upgrade head` ผ่าน
- `alembic check` ผ่านและไม่พบ schema drift
- `npm run build` ผ่าน TypeScript และ Vite production build
- FastAPI start-up, `/api/v1/health` และ `/openapi.json` ผ่าน
- Backend และ frontend production Docker image build ผ่าน
- Production Compose configuration validation ผ่าน
- Full Compose cold start, HTTPS reverse proxy, Admin bootstrap, login และ protected API smoke test ผ่าน
- Database backup/checksum/isolated restore rehearsal ผ่าน และมีสคริปต์ป้องกัน restore ทับชื่อฐาน production
- Database outage/recovery ผ่าน: processes ไม่ตาย, backend กลับ healthy, worker cycle และ scheduler retry ฟื้นเอง
- ลบ embedded development credentials ออกจาก application config และบังคับ production secret แบบ explicit
- Isolated LINE webhook relay template พร้อม path/method/body/rate controls และ Docker DNS re-resolution
- Webhook relay rehearsal ผ่าน valid/invalid HMAC, deduplication, rate limit, body limit และ backend recreate
- Frontend Nginx re-resolve backend ผ่าน Docker DNS; HTTPS UI/API ยัง 200 หลัง backend container recreate

## ข้อจำกัดและงานคงเหลือ

- Google Sheets/Drive production adapters ยังเป็น mock contract; durable staging/retry พร้อมแล้ว
- Natural-language LINE Q&A ยังต้องต่อจาก provider contract
- Gemini production adapter ยังปิดใช้งาน
- Playwright browser test ยังรันไม่ได้ เพราะ Cloud Desktop ไม่มี browser runtime และ CDN ดาวน์โหลด Chromium ตอบ 403
- Public internet/TLS tunnel จริงและ browser E2E ยังไม่ได้รัน
- Private GitHub repository พร้อมใช้งานผ่าน GitHub connector แม้ GitHub CLI token ยังใช้ไม่ได้
- ไม่มี credentials จริง จึงไม่ได้ทดสอบหรือส่ง LINE/Google/Gemini จริง

## Next actions

1. ทำ Google Sheets/Drive production adapters และ conflict resolution UI
2. ทำ deterministic LINE Q&A และ reply adapter
3. เพิ่ม browser E2E เมื่อมี browser runtime
4. ทดสอบ public TLS/tunnel กับ LINE Verify Webhook หลังได้รับ credentials และอนุมัติ network
5. ทำ acceptance rehearsal ด้วยข้อมูลจำลองก่อนเชื่อม credentials จริง

## Latest Git commit

Milestone: `core domain, PostgreSQL workflow, Thai dashboard` ตรวจ hash ปัจจุบันด้วย `git rev-parse HEAD`

