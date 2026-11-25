# Codex working agreement

- ตอบผู้ใช้และเขียนคู่มือผู้ใช้เป็นภาษาไทย
- SQL Server/BA_PMnotification เป็นแหล่งข้อมูลจริงเพียงแห่งเดียว และ SSMS ใช้จัดการฐานข้อมูล
- ห้ามเพิ่มสถานะ `COMPLETED` หรืออนุมานว่างาน PM เสร็จจากวันนัดหรือการยืนยันนัด
- ห้ามส่ง LINE จริง เปิดระบบสู่ภายนอก หรือ deploy production หากไม่มีคำสั่งชัดเจน
- ห้าม commit secrets หรือข้อมูลลูกค้า
- ใช้ mock adapters ในการพัฒนาเมื่อไม่มี credentials
- ก่อนจบ milestone ให้รัน test ที่เกี่ยวข้องและอัปเดต `PROGRESS.md` กับ `TEST_REPORT.md`
- repository เดิมใน workspace เป็นคนละระบบ ห้ามอ่าน secret เชื่อมฐานข้อมูล หรือแก้ไขไฟล์ของระบบเดิม

