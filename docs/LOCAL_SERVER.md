# ติดตั้งบน Company Local Server

## รูปแบบแนะนำ

ใช้ Linux VM บน Windows host หรือ container runtime ที่รองรับ Docker Compose ให้ LAN/VPN เข้า HTTPS reverse proxy เท่านั้น PostgreSQL, Docker socket และ OS administration ต้องไม่เปิดสู่ internet

1. Clone private repository เข้า VM
2. คัดลอก `.env.example` เป็น `.env` และเปลี่ยนทุก secret
3. ตั้ง `APP_HOST`, `POSTGRES_PASSWORD`, `SECRET_KEY` และ account bootstrap
4. รัน `docker compose -f deploy/local/compose.yaml build`
5. รัน migration ด้วย backend container
6. สร้าง Admin คนแรกแบบ interactive
7. รัน `docker compose -f deploy/local/compose.yaml up -d`
8. ตรวจ `/api/v1/health`, worker status, volumes และ log rotation

ถ้าองค์กรใช้ TLS inspection และ build ติด `SELF_SIGNED_CERT_IN_CHAIN` ให้ส่ง corporate CA เป็น BuildKit secret โดยไม่ copy certificate เข้า repository หรือ image:

```bash
docker build --secret id=ca,src=/path/to/company-ca.crt -t ba-chiller-backend ./backend
docker build --secret id=ca,src=/path/to/company-ca.crt -t ba-chiller-frontend ./frontend
```

ห้ามแก้ด้วยการปิด TLS verification หรือใช้ `--trusted-host`

Dashboard ใช้ได้ใน LAN เมื่อ internet ขัดข้อง ส่วน LINE และ Google jobs จะรอ retry

## Webhook gateway

FortiGate VPN อย่างเดียวไม่ทำให้ LINE เรียก private LAN endpoint ได้ ใช้ public HTTPS relay ที่ตรวจ path, จำกัดขนาด body, rate limit และส่งต่อผ่าน outbound authenticated tunnel ไป local server การตรวจ LINE signature ยังคงทำซ้ำที่ FastAPI ห้ามเปิด PostgreSQLหรือ administrative ports ผ่าน gateway

## Rollback

เก็บ image tag และ database backup ก่อน release ถ้า application มีปัญหาให้ย้อน image tag แล้วใช้ migration downgrade เฉพาะ revision ที่ผ่านการทดสอบ ห้าม restore ฐานทับข้อมูลใหม่โดยไม่ตรวจ recovery point

