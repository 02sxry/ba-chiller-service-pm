# LINE Webhook Relay

ไฟล์ใน `deploy/relay/` เป็น gateway template สำหรับวางหลัง public TLS endpoint หรือ authenticated tunnel เท่านั้น ไม่ใช่คำสั่งให้เปิด local server สู่อินเทอร์เน็ตโดยตรง

Relay อนุญาตเฉพาะ `POST /api/v1/line/webhook`, จำกัด body 1 MiB, rate 10 requests/second ต่อ IP พร้อม burst 20, ส่งต่อ `X-Line-Signature` และตั้ง timeout สั้น FastAPI จะตรวจ HMAC ซ้ำบน raw body และ deduplicate `webhookEventId`

## Isolated rehearsal

เมื่อ local Compose stack ทำงานอยู่:

```bash
docker compose -f deploy/relay/compose.yaml up -d
curl -i http://127.0.0.1:18080/not-allowed
curl -i -X POST http://127.0.0.1:18080/api/v1/line/webhook -d '{}'
docker compose -f deploy/relay/compose.yaml down
```

ผลที่คาดคือ path อื่นได้ 404 และ webhook ที่ไม่มี credential/signature ได้ 503 จาก backend ห้ามลดการตรวจ signature ที่ application แม้ relay จะมี authentication ของตัวเอง

## ก่อนใช้งานจริง

- ให้ public endpoint รับ TLS จาก CA ที่ LINE เชื่อถือ และส่งต่อผ่าน outbound authenticated tunnel
- จำกัด firewall ให้ relay เข้าถึงเฉพาะ backend webhook port/path
- ไม่เปิด PostgreSQL, Docker socket, dashboard admin หรือ host administration
- เก็บ access log ตามนโยบายโดยไม่บันทึก channel secret/token หรือ request body
- ทดสอบ LINE Verify Webhook ด้วย credentials แยกและคง notification kill switch ไว้
