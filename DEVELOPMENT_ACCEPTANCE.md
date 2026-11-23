# รายงานรับมอบงานพัฒนา ณ Milestone ปัจจุบัน

## สถานะ

ระบบผ่าน milestone สำหรับ core domain, operational integration และ local production runtime ยังไม่พร้อมรับ development acceptance ตาม Definition of Done ฉบับเต็ม เนื่องจาก production adapters, public TLS/tunnel จริง และ browser E2E ยังไม่ครบ

## ใช้งานได้แล้ว

- PostgreSQL migration และ authoritative business state
- Authentication/role enforcement foundation
- Hospital/Equipment master data และ dependent Draft review ถึง PM Plan
- Annual plan, PM Slot และ next-year drafts
- Thai text/XLSX parsing foundation
- Slot recommendation
- Appointment approval, hospital confirmation/reschedule และ immutable revision history
- Technician change after confirmation โดยไม่บังคับ reconfirm
- Audit/outbox/webhook security foundation
- Thai dashboard และ core forms บางส่วน
- Equipment/PM plan forms, intake queue และ appointment calendar/history views
- LINE Flex confirm/reschedule, postback routing และ group authorization
- Google hospital staging sync, conflict preservation และ bounded mock retry
- Reports, LINE Groups, Google operations และ Settings views
- Mock integration mode และ local deployment artifacts
- Backend/frontend production image build และ Compose configuration validation
- Full Compose cold start, HTTPS proxy และ Admin bootstrap/login smoke path
- Database backup/checksum และ isolated restore rehearsal
- Database outage/recovery ของ backend, worker และ scheduler
- Isolated webhook relay controls, HMAC/dedup และ backend restart recovery

## สิ่งที่ทดสอบจริง

ดู `TEST_REPORT.md` ผลล่าสุดคือ backend 39 tests ผ่าน, lint/build/migration/schema check/API health, Docker image build, full Compose smoke และ database recovery ผ่าน

## สิ่งที่ยังไม่ยืนยัน

Real external integrations, public TLS/tunnel และ browser E2E

## เริ่มระบบ

ทำตาม `README.md` ใช้ PostgreSQL dev container รัน Alembic สร้าง Admin คนแรก แล้วเริ่ม FastAPI และ Vite

## Mock LINE และ Google

ปล่อย credentials ว่าง คง `NOTIFICATIONS_ENABLED=false` และ `NOTIFICATION_KILL_SWITCH=true` API health จะแสดง LINE/Google เป็น mock โดยไม่มีข้อมูลส่งออก

## Production authorization

ต้องได้รับอนุมัติก่อน deploy production, เชื่อม production database/credentials, เปิด public webhook, เปลี่ยน FortiGate, เปิด notification และส่ง LINE จริง

