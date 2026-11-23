# Backup และ Restore

## Backup รายวัน

```bash
docker compose -f deploy/local/compose.yaml exec -T db \
  pg_dump -U ba_chiller -d ba_chiller -Fc > ba_chiller_YYYYMMDD.dump
```

เข้ารหัสไฟล์ backup เก็บนอก host และกำหนด retention ตามนโยบายบริษัท Google Drive source files ต้องมี backup policy แยกจาก database

## Restore rehearsal

สร้างฐานข้อมูลว่างใน isolated environment แล้วรัน

```bash
pg_restore --clean --if-exists --no-owner --dbname=ba_chiller_restore ba_chiller_YYYYMMDD.dump
```

ตรวจจำนวน hospitals, equipment, plans, slots, appointments, revisions, notification jobs และ audit logs จากนั้นเปิด API health และทดสอบ read-only reports ห้ามทดสอบ restore ทับ production โดยตรง

