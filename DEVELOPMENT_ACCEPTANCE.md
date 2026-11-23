# รายงานรับมอบงานพัฒนา ณ Milestone ปัจจุบัน

## สถานะ

ระบบผ่าน milestone สำหรับ core domain และ integration-ready architecture ยังไม่พร้อมรับ development acceptance ตาม Definition of Done ฉบับเต็ม เนื่องจาก production adapters, dependent drafts บางชนิด, frontend operational screens และ browser E2E ยังไม่ครบ

## ใช้งานได้แล้ว

- PostgreSQL migration และ authoritative business state
- Authentication/role enforcement foundation
- Hospital master data และ Hospital Draft review
- Annual plan, PM Slot และ next-year drafts
- Thai text/XLSX parsing foundation
- Slot recommendation
- Appointment approval, hospital confirmation/reschedule และ immutable revision history
- Technician change after confirmation โดยไม่บังคับ reconfirm
- Audit/outbox/webhook security foundation
- Thai dashboard และ core forms บางส่วน
- Equipment/PM plan forms, intake queue และ appointment calendar/history views
- Mock integration mode และ local deployment artifacts

## สิ่งที่ทดสอบจริง

ดู `TEST_REPORT.md` ผลล่าสุดคือ backend 23 tests ผ่าน, lint/build/migration/schema check/API health ผ่าน

## สิ่งที่ยังไม่ยืนยัน

Real external integrations, production container build, restore rehearsal, browser E2E, worker outage recovery และหน้าปฏิบัติการที่ยังเป็น placeholder

## เริ่มระบบ

ทำตาม `README.md` ใช้ PostgreSQL dev container รัน Alembic สร้าง Admin คนแรก แล้วเริ่ม FastAPI และ Vite

## Mock LINE และ Google

ปล่อย credentials ว่าง คง `NOTIFICATIONS_ENABLED=false` และ `NOTIFICATION_KILL_SWITCH=true` API health จะแสดง LINE/Google เป็น mock โดยไม่มีข้อมูลส่งออก

## Production authorization

ต้องได้รับอนุมัติก่อน deploy production, เชื่อม production database/credentials, เปิด public webhook, เปลี่ยน FortiGate, เปิด notification และส่ง LINE จริง

