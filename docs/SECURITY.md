# Security design

- Password hash ใช้ Argon2 และ access token มีอายุจำกัด
- Backend route บังคับ Admin/Viewer แยกกัน ไม่อาศัยการซ่อนปุ่ม frontend
- Admin คนแรกสร้างผ่าน interactive script ไม่มี default password
- LINE webhook ตรวจ signature จาก raw body และ deduplicate event
- Hospital action token เป็น random token เก็บเฉพาะ SHA-256 hash มีวันหมดอายุ ใช้ได้ครั้งเดียว และผูก revision
- Hospital group ต้อง map กับ hospital record ก่อนอ่านหรือตอบนัด
- Upload จำกัดขนาดและรับ `.xlsx` เท่านั้น ใช้ openpyxl แบบ read-only/data-only และไม่ execute macro
- Secrets อยู่ใน environment/secret store และต้องไม่ commit
- Logs ห้ามบันทึก token, password, private key หรือ raw credential
- Caddy เพิ่ม security headers และเปิดเฉพาะ HTTPS application endpoint
- PostgreSQL อยู่ใน private container network ไม่มี public exposure ใน production compose

