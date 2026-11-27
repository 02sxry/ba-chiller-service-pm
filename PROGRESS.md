# Progress

## Local UAT — 27 พฤศจิกายน 2026

- แก้ migration ภาษาไทยสำหรับฐานเดิมที่ติดดัชนีใน SQL Server และรองรับ Unicode ในข้อความช่าง หมายเหตุ และประวัติ
- เชื่อมกลุ่มช่างเข้ากับคิวอนุมัติแล้ว ผู้ดูแลเลือกรอบ PM ดูข้อความตัวอย่าง และสร้างนัดจากรายการที่ช่างส่งได้
- ผ่านการอัปเกรดฐานเดิมและฐานว่าง ทดสอบ Backend 64 รายการ และทดสอบเส้นทางกรอกข้อมูลถึง Archive ผ่าน Chromium บน SQL Server แยก รายละเอียดอยู่ใน `TEST_REPORT.md`
- รอยืนยันผล migration และบันทึกข้อมูลภาษาไทยบน SQLEXPRESS ของผู้ใช้ การทดสอบ LINE รอบนี้ใช้ Webhook และการส่งข้อความแบบจำลอง

อัปเดตล่าสุด 23 พฤศจิกายน 2026 เวลา Asia/Bangkok

## Milestone ปัจจุบัน

Operational integration milestone: Google provider adapter และ container build

## ทำแล้ว

- สร้างโปรเจกต์ `BA_PMnotification` โดยไม่แก้ repository เดิม
- FastAPI app, centralized settings/error handling, CORS และ OpenAPI
- SQL Server schema และ Alembic initial migration 26 ตาราง
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
- Docker Compose สำหรับ backend ที่เชื่อม SQL Server และ local production stack
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
- Google Drive upload ตรวจ folder kind, ค้นหาโฟลเดอร์เป้าหมายใต้ root และปฏิเสธ missing/duplicate folder ก่อน upload
- LINE Messaging API production adapter แบบ opt-in พร้อม HTTP error handling และ mock fallback
- Gemini intent provider แบบ opt-in พร้อม JSON contract validation, temperature 0 และ safe deterministic fallback
- Full local Compose stack ผ่าน cold start, migration, health, login และ protected dashboard smoke test
- Frontend proxy ส่ง `/openapi.json` ไป backend โดยตรงเพื่อให้ API docs ใช้งานได้ครบ
- Schedule intake เรียก Gemini เฉพาะรายการที่ deterministic parser ระบุว่า NEEDS_REVIEW และเก็บเป็นคำแนะนำแยกจากข้อมูล parsed หลัก
- Deterministic LINE Q&A รองรับเมนูช่วยเหลือและดูนัดหมายของ hospital group ที่ authorize แล้ว
- LINE Q&A ใช้ notification outbox เดิม, มี idempotency ต่อ webhook event และไม่ส่งจริงเมื่อ kill switch เปิด
- เพิ่มคู่มือทดลองบนโน้ตบุ๊กด้วย Docker Desktop ตั้งแต่ clone, สร้าง `.env`, bootstrap Admin, smoke check, test flow และ backup ก่อนย้าย server
- เปลี่ยน Login เป็น User ID + Password พร้อม username migration และ local Admin เริ่มต้น `admin/admin` โดยยังเก็บ email เดิมไว้เพื่อความเข้ากันได้ของข้อมูลเก่า
- เพิ่มตัวกรองรอบ PM ตามโรงพยาบาล เครื่อง รุ่น ปี และเดือน พร้อมไฟล์ Google Sheets workbook template ที่มีชีตเริ่มต้นและคำอธิบายภาษาไทย
- เพิ่มหน้า Admin กรอกข้อมูลฐานข้อมูลหน้าเดียว พร้อมแก้ไขและปิดใช้งานโรงพยาบาล/อุปกรณ์ โดยไม่ลบประวัติถาวร
- ปรับ local password policy เป็นอย่างน้อย 4 ตัว และเพิ่มคำสั่ง `ensure-admin` สำหรับซ่อม User ID `admin` ให้เป็น ADMIN
- เพิ่ม Admin user management: แก้ไขชื่อ/สิทธิ์/รหัสผ่าน และปิดใช้งาน User พร้อมป้องกันปิดตัวเองหรือปิด Admin คนสุดท้าย
- หน้าโรงพยาบาลแสดงเฉพาะรายการที่ยังใช้งานอยู่ รายการที่ Admin ปิดใช้งานจะไม่แสดง และแยก cache รายการ active/all ป้องกันข้อมูลข้ามหน้าปะปนกัน
- ช่องเลือกสร้างแผน PM แสดงโรงพยาบาล ชื่ออุปกรณ์ รุ่น เลขเครื่อง และสถานที่ติดตั้ง พร้อมแสดงเลขเครื่องในหน้ารายการอุปกรณ์

## Tests executed

- `pytest -q` กับ SQL Server จริง ต้องรันบนเครื่องที่มี SQL Server และ ODBC Driver 18
- `ruff check app tests alembic --exclude alembic/versions` ผ่าน
- `alembic upgrade head` ผ่าน
- `alembic check` ผ่านและไม่พบ schema drift
- `npm run build` ผ่าน TypeScript และ Vite production build
- FastAPI start-up, `/api/v1/health` และ `/openapi.json` ผ่าน
- compatibility tests ผ่านหลังเปลี่ยนเป็น SQL Server-only
- `ruff check app tests alembic --exclude alembic/versions` ผ่านหลังเพิ่ม Google adapter
- `npm ci && npm run build` ผ่าน TypeScript และ Vite production build
- Google retry endpoint และ Sync operations UI ผ่าน regression suite เดิมโดยไม่เพิ่ม schema/migration
- LINE question parser, appointment lookup และ bounded text payload ผ่าน tests
- Google Sheets stable-row update ผ่าน provider contract test โดยไม่ใช้ workbook จริง
- Google Drive folder routing ผ่าน contract test โดยไม่ upload ไฟล์จริง
- LINE provider payload/auth/error handling ผ่าน contract tests โดยไม่เรียก LINE จริง
- Gemini valid/invalid response handling ผ่าน contract tests โดยไม่เรียก Gemini จริง
- Intake AI suggestion ถูกเก็บแบบ review-only และไม่เปลี่ยน state/นัดหมายอัตโนมัติ
- Local server smoke: backend, frontend, worker, scheduler และ Caddy เชื่อม SQL Server; health/login/dashboard ผ่าน HTTP 200
- Backend และ frontend production Docker image build ผ่าน
- Production Compose configuration validation ผ่าน
- Full Compose cold start, HTTPS reverse proxy, Admin bootstrap, login และ protected API smoke test ผ่าน
- Database backup/checksum/isolated restore rehearsal ผ่าน และมีสคริปต์ป้องกัน restore ทับชื่อฐาน production
- Database outage/recovery ผ่าน: processes ไม่ตาย, backend กลับ healthy, worker cycle และ scheduler retry ฟื้นเอง
- ลบ embedded development credentials ออกจาก application config และบังคับ production secret แบบ explicit
- Isolated LINE webhook relay template พร้อม path/method/body/rate controls และ Docker DNS re-resolution
- Webhook relay rehearsal ผ่าน valid/invalid HMAC, deduplication, rate limit, body limit และ backend recreate
- Frontend Nginx re-resolve backend ผ่าน Docker DNS; HTTPS UI/API ยัง 200 หลัง backend container recreate
- Google workbook template: สร้างไฟล์ XLSX ได้จริง ตรวจสอบชื่อชีตและหัวคอลัมน์ครบ รวมชีต `เริ่มที่นี่`
- Backend compile และ frontend production build ผ่านหลังเพิ่ม API แก้ไข/ปิดใช้งานและ Admin-only database entry page
- Frontend production build ผ่านหลังซ่อนโรงพยาบาลที่ปิดใช้งานและแยก React Query cache ตามขอบเขตข้อมูล
- Frontend production build ผ่านหลังเพิ่มข้อมูลระบุตัวอุปกรณ์ในหน้ารายการและตัวเลือกสร้างแผน PM

## ข้อจำกัดและงานคงเหลือ

- Google Sheets/Drive production adapter เพิ่มแล้ว แต่ยังไม่ได้ทดสอบกับ credentials/ไฟล์จริง
- Natural-language LINE Q&A ยังต้องต่อจาก provider contract
- Gemini production adapter ยังปิดใช้งาน
- Playwright browser test ยังรันไม่ได้ เพราะ Cloud Desktop ไม่มี browser runtime และ CDN ดาวน์โหลด Chromium ตอบ 403
- Public internet/TLS tunnel จริงและ browser E2E ยังไม่ได้รัน
- Private GitHub repository พร้อมใช้งานผ่าน GitHub connector แม้ GitHub CLI token ยังใช้ไม่ได้
- ไม่มี credentials จริง จึงไม่ได้ทดสอบหรือส่ง LINE/Google/Gemini จริง

## Next actions

1. เปิดใช้งาน Google Sheets sync สำหรับ Equipment และ PM Plans ต่อจาก Hospitals_Input
2. เพิ่ม Admin UI สำหรับ approve/reject AI suggestion โดยไม่เขียนทับ parsed source
3. เพิ่ม browser E2E เมื่อมี browser runtime
4. ทดสอบ public TLS/tunnel กับ LINE Verify Webhook หลังได้รับ credentials และอนุมัติ network
5. ทำ acceptance rehearsal ด้วยข้อมูลจำลองก่อนเชื่อม credentials จริง

## Latest Git commit

Milestone: `core domain, SQL Server workflow, Thai dashboard` ตรวจ hash ปัจจุบันด้วย `git rev-parse HEAD`

