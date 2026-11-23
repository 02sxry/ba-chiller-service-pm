# Progress

อัปเดตล่าสุด 23 พฤศจิกายน 2026 เวลา Asia/Bangkok

## Milestone ปัจจุบัน

Operational integration milestone: Google provider adapter และ container build

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
- Google production adapter แบบ opt-in สำหรับ Sheets append และ Drive upload ด้วย service account
- Google provider factory แยก mock/production ชัดเจน โดยค่าเริ่มต้นยังปลอดภัยเป็น mock
- เพิ่ม Google API SDK ใน lockfile และตั้งค่า `GOOGLE_SERVICE_ACCOUNT_FILE` / `GOOGLE_USE_REAL_PROVIDER`
- Google operations มีปุ่ม Admin สั่งส่งซ้ำ/ลองใหม่สำหรับ outbound sync event พร้อม audit log
- Google Sheets export ใช้ `row_key`/`record_id` ค้นหาและ update แถวเดิมก่อน append ป้องกัน retry สร้างข้อมูลซ้ำ
- Deterministic LINE Q&A รองรับเมนูช่วยเหลือและดูนัดหมายของ hospital group ที่ authorize แล้ว
- LINE Q&A ใช้ notification outbox เดิม, มี idempotency ต่อ webhook event และไม่ส่งจริงเมื่อ kill switch เปิด

## Tests executed

- `pytest -q` กับ PostgreSQL 17 จริง ผ่าน 39 tests
- `ruff check app tests alembic --exclude alembic/versions` ผ่าน
- `alembic upgrade head` ผ่าน
- `alembic check` ผ่านและไม่พบ schema drift
- `npm run build` ผ่าน TypeScript และ Vite production build
- FastAPI start-up, `/api/v1/health` และ `/openapi.json` ผ่าน
- `pytest -q` ผ่าน 42 tests หลังเปิด PostgreSQL 17 isolated container
- `ruff check app tests alembic --exclude alembic/versions` ผ่านหลังเพิ่ม Google adapter
- `npm ci && npm run build` ผ่าน TypeScript และ Vite production build
- Google retry endpoint และ Sync operations UI ผ่าน regression suite เดิมโดยไม่เพิ่ม schema/migration
- LINE question parser, appointment lookup และ bounded text payload ผ่าน tests
- Google Sheets stable-row update ผ่าน provider contract test โดยไม่ใช้ workbook จริง
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

- Google Sheets/Drive production adapter เพิ่มแล้ว แต่ยังไม่ได้ทดสอบกับ credentials/ไฟล์จริง
- Natural-language LINE Q&A ยังต้องต่อจาก provider contract
- Gemini production adapter ยังปิดใช้งาน
- Playwright browser test ยังรันไม่ได้ เพราะ Cloud Desktop ไม่มี browser runtime และ CDN ดาวน์โหลด Chromium ตอบ 403
- Public internet/TLS tunnel จริงและ browser E2E ยังไม่ได้รัน
- Private GitHub repository พร้อมใช้งานผ่าน GitHub connector แม้ GitHub CLI token ยังใช้ไม่ได้
- ไม่มี credentials จริง จึงไม่ได้ทดสอบหรือส่ง LINE/Google/Gemini จริง

## Next actions

1. เพิ่ม Google export reconciliation หลายแถวและ conflict resolution UI
2. เพิ่ม LINE reply adapter จริงเมื่อได้รับ channel credentials และอนุมัติการส่งข้อความ
3. เพิ่ม browser E2E เมื่อมี browser runtime
4. ทดสอบ public TLS/tunnel กับ LINE Verify Webhook หลังได้รับ credentials และอนุมัติ network
5. ทำ acceptance rehearsal ด้วยข้อมูลจำลองก่อนเชื่อม credentials จริง

## Latest Git commit

Milestone: `core domain, PostgreSQL workflow, Thai dashboard` ตรวจ hash ปัจจุบันด้วย `git rev-parse HEAD`

