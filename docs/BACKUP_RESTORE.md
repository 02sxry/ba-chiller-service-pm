# Backup และ Restore

## Backup รายวัน

```bash
./scripts/backup_database.sh
# หรือระบุปลายทางเอง
./scripts/backup_database.sh /secure/path/ba_chiller_YYYYMMDD.dump
```

สคริปต์ไม่เขียนทับไฟล์เดิม ตั้ง permission ตาม `umask 077` และสร้างไฟล์ `.sha256` คู่กัน เข้ารหัส backup เก็บนอก host และกำหนด retention ตามนโยบายบริษัท Google Drive source files ต้องมี backup policy แยกจาก database

## Restore rehearsal

สร้างฐานข้อมูลว่างใน isolated environment แล้วรัน

```bash
./scripts/restore_rehearsal.sh /secure/path/ba_chiller_YYYYMMDD.dump
```

สคริปต์ยอมให้ restore เฉพาะฐาน `ba_chiller_restore` หรือชื่อที่ขึ้นต้นด้วย `ba_chiller_restore_` และพิมพ์จำนวนข้อมูลสำคัญหลัง restore จากนั้นเปิด API health และทดสอบ read-only reports ห้ามทดสอบ restore ทับ production โดยตรง

