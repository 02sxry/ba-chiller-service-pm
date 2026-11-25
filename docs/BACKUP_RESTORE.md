# Backup และ Restore ของ SQL Server

## Backup รายวัน

```bash
./scripts/backup_database.sh
# หรือระบุปลายทางเอง
./scripts/backup_database.sh /secure/path/BA_PMnotification_YYYYMMDD.dump
```

ตั้งค่า `SQLSERVER_HOST`, `SQLSERVER_DATABASE`, `SQLSERVER_USER`, `SQLSERVER_PASSWORD` และ `SQLSERVER_BACKUP_PATH` แล้วสคริปต์จะสั่ง `BACKUP DATABASE` ผ่าน `sqlcmd` ไม่เขียนทับไฟล์เดิม ตั้ง permission ตาม `umask 077` และสร้างไฟล์ `.sha256` คู่กัน เก็บ backup นอก host และกำหนด retention ตามนโยบายบริษัท Google Drive source files ต้องมี backup policy แยกจาก database

## Restore rehearsal

ใช้ไฟล์ backup บน path ที่ SQL Server เข้าถึงได้ แล้วรัน

```bash
./scripts/restore_rehearsal.sh /secure/path/BA_PMnotification_YYYYMMDD.dump
```

สคริปต์ยอมให้ restore เฉพาะฐาน `BA_PMnotification_restore` หรือชื่อที่ขึ้นต้นด้วย `BA_PMnotification_restore_` และพิมพ์จำนวนข้อมูลสำคัญหลัง restore จากนั้นเปิด API health และทดสอบ read-only reports ห้ามทดสอบ restore ทับ production โดยตรง

