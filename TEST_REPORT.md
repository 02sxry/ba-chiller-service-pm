# Test Report

วันที่ทดสอบ 23 พฤศจิกายน 2026

## ผลที่ผ่าน

| ชุดทดสอบ | ผล | หลักฐาน |
|---|---:|---|
| Backend business rules | 25 passed | pytest กับ PostgreSQL 17 container, 0 failed |
| Python lint | ผ่าน | Ruff ตรวจ app, tests และ Alembic environment |
| PostgreSQL migration | ผ่าน | Alembic upgrade revision `1b6004596e27` |
| Schema drift | ผ่าน | Alembic check รายงาน `No new upgrade operations detected` |
| Frontend type/build | ผ่าน | TypeScript build และ Vite production bundle |
| API startup | ผ่าน | Uvicorn start สำเร็จ |
| Health endpoint | ผ่าน | database `ok`, LINE/Google `mock`, Gemini/notifications disabled |
| OpenAPI | ผ่าน | HTTP 200, schema 29,311 bytes ณ เวลาทดสอบ |

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

## ไม่ผ่านหรือยังรันไม่ได้

- Cloud Desktop เปิด browser ไม่ได้เพราะ browser runtime unavailable
- Playwright ดาวน์โหลด Chromium ไม่ได้เพราะ CDN ตอบ HTTP 403 จึงยังไม่มี visual/E2E browser result
- Real LINE, Google Sheets, Google Drive และ Gemini ไม่ได้ทดสอบเพราะไม่มี credentials และไม่มีสิทธิ์ส่งจริง
- Production Compose image build, backup restore และ network outage recovery ยังไม่ได้ทดสอบ

ไม่มีการนับรายการที่ไม่ได้รันเป็น test ผ่าน

