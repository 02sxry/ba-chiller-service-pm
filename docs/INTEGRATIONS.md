# คู่มือ LINE, Google Workspace และ Gemini

## โหมดพัฒนา

ไม่ต้องใช้ credentials ระบบมี mock adapters และ `NOTIFICATIONS_ENABLED=false`, `NOTIFICATION_KILL_SWITCH=true` เป็นค่าเริ่มต้น Mock provider สร้าง provider reference จำลองและไม่ส่งข้อมูลออกภายนอก

## LINE Messaging API

1. สร้าง LINE Messaging API channel แยกจากระบบเดิม
2. เก็บ Channel Secret และ Channel Access Token ใน secret store หรือ `.env` ของเครื่องปลายทาง
3. ตั้ง webhook เป็น public HTTPS URL ที่ส่งต่อเฉพาะ `/api/v1/line/webhook`
4. ลงทะเบียน LINE group ID กับ hospital ID ผ่านสิทธิ์ Admin
5. เปิด `NOTIFICATIONS_ENABLED=true` หลังทดสอบ allowlist แล้ว
6. คง kill switch ไว้จนผ่าน production readiness review

Webhook ตรวจ HMAC-SHA256 บน raw body, deduplicate ด้วย `webhookEventId` และตรวจ action token, revision และ group authorization ที่ server
ดู gateway controls และ isolated rehearsal ใน [LINE Webhook Relay](WEBHOOK_RELAY.md)

## Google Sheets

ระบบมี Google API adapter สำหรับ production แล้ว แต่ปิดไว้โดยค่าเริ่มต้นเพื่อป้องกันการส่งข้อมูลโดยไม่ตั้งใจ

กำหนดค่าบนเครื่องปลายทางเมื่อพร้อมเชื่อมต่อจริง:

```dotenv
GOOGLE_SPREADSHEET_ID=...
GOOGLE_DRIVE_ROOT_FOLDER_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/google-service-account.json
GOOGLE_USE_REAL_PROVIDER=true
```

Service account ต้องมีสิทธิ์แก้ไขเฉพาะ workbook และโฟลเดอร์ที่กำหนดเท่านั้น ห้าม commit JSON key ลง Git
และควร mount ผ่าน secret store ของเครื่อง local server

สร้าง workbook template ด้วย

```bash
python scripts/create_workbook_template.py output/BA_PMnotification_MASTER.xlsx
```

ไฟล์ Template ที่สร้างไว้ใน repository คือ [`output/BA_PMnotification_MASTER.xlsx`](../output/BA_PMnotification_MASTER.xlsx)
ให้อัปโหลดไฟล์นี้เข้า Google Drive แล้วเลือก `Open with Google Sheets` จากนั้นแชร์ให้ service account
ที่ใช้กับระบบเป็น Editor เฉพาะไฟล์นี้เท่านั้น ชีต `เริ่มที่นี่` อธิบายหน้าที่ของแต่ละคอลัมน์ไว้แล้ว

Input tabs ใช้ `row_key`, `record_id`, `expected_version`, `operation`, `validation_status`, `validation_errors`, `processed_at` Reporting tabs เป็น projection จาก SQL Server ห้ามกรอก APPROVED ใน cell เพื่อแทนการอนุมัติของ Admin

## Google Drive

ให้ service account หรือ OAuth client เข้าถึงเฉพาะ folders ที่กำหนด ได้แก่ Technician_Schedules_Inbox, Technician_Schedules_Processed, Technician_Schedules_Rejected, Equipment_Documents และ Generated_Reports บันทึก Drive file ID และ checksum ใน SQL Server และไม่เปิด public sharing

## Gemini

Deterministic parser ทำงานก่อน Gemini ใช้เพื่อจัด intent และแยก parameter เมื่อข้อความซับซ้อนเท่านั้น Output ทุกครั้งต้องผ่าน Pydantic validation Gemini ไม่สร้าง SQL ไม่ยืนยัน master data และไม่อนุมัตินัด

