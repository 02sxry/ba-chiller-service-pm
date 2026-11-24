# คู่มือทดลองบนโน้ตบุ๊ก

คู่มือนี้ใช้สำหรับทดลองระบบบน Windows 10/11 หรือ macOS/Linux ด้วย Docker Desktop โดยใช้ฐานข้อมูลและ integration แบบ local/mock เท่านั้น ข้อมูลจากโน้ตบุ๊กไม่ใช่ข้อมูล production

## สิ่งที่ต้องติดตั้ง

- Docker Desktop ที่เปิดใช้งาน Docker Compose ได้
- Git
- RAM แนะนำอย่างน้อย 8 GB และพื้นที่ว่างอย่างน้อย 10 GB

ไม่ต้องติดตั้ง Python หรือ Node.js หากใช้วิธี Docker Compose ในคู่มือนี้

## ลิงก์ดาวน์โหลดสำหรับ Windows

ถ้าทดลองด้วย Docker Desktop ให้ติดตั้งเฉพาะ Docker Desktop และ Git:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git for Windows](https://git-scm.com/download/win)

ถ้าไม่ใช้ Docker Desktop ให้ติดตั้งเพิ่มเอง:

- [Python 3.12 ขึ้นไป](https://www.python.org/downloads/windows/) — ตอนติดตั้งให้ติ๊ก `Add Python to PATH`
- [Node.js 24 ขึ้นไป](https://nodejs.org/en/download)
- [PostgreSQL สำหรับ Windows](https://www.postgresql.org/download/windows/)

ขั้นตอนด้านล่างของคู่มือนี้เป็น Docker Compose ส่วนวิธีติดตั้งแบบไม่ใช้ Docker อยู่ในหัวข้อท้ายคู่มือ

## 1. ดาวน์โหลดและสร้างไฟล์ตั้งค่า

เปิด PowerShell หรือ Terminal แล้วรัน:

```bash
git clone https://github.com/02sxry/ba-chiller-service-pm.git
cd ba-chiller-service-pm
```

สร้าง `.env` จากตัวอย่าง:

```powershell
Copy-Item .env.example .env
```

บน macOS/Linux ใช้ `cp .env.example .env`

เปิดไฟล์ `.env` แล้วใส่ค่า local อย่างน้อยดังนี้:

```dotenv
APP_ENV=development
APP_HOST=localhost
SECRET_KEY=local-notebook-secret-change-before-server
POSTGRES_PASSWORD=local-notebook-db-password
DATABASE_URL=postgresql+psycopg://ba_chiller:local-notebook-db-password@db:5432/ba_chiller
DATABASE_URL_SYNC=postgresql+psycopg://ba_chiller:local-notebook-db-password@db:5432/ba_chiller
FRONTEND_ORIGIN=http://localhost
NOTIFICATIONS_ENABLED=false
NOTIFICATION_KILL_SWITCH=true
GOOGLE_USE_REAL_PROVIDER=false
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
GEMINI_API_KEY=
```

สำคัญ: ใน `DATABASE_URL` ต้องใช้ host เป็น `db` เพราะ backend อยู่ใน Compose network ไม่ใช่ `localhost` และห้าม commit หรือส่งไฟล์ `.env` ให้ผู้อื่น

## 2. เปิดระบบ

```bash
docker compose --env-file .env -f deploy/local/compose.yaml up -d
docker compose --env-file .env -f deploy/local/compose.yaml ps
```

รอจน `db` และ `backend` เป็น `healthy` หากต้องดู log:

```bash
docker compose --env-file .env -f deploy/local/compose.yaml logs --tail=100 backend worker scheduler
```

ถ้า Docker build ขึ้น `UnknownIssuer`, `SELF_SIGNED_CERT_IN_CHAIN` หรือปัญหา TLS ขององค์กร ให้ใช้ corporate CA ขององค์กรเป็น BuildKit secret (ไม่ต้อง copy เข้า repo):

```bash
docker build --secret id=ca,src=/path/to/company-ca.crt -t local-backend -t local-worker -t local-scheduler ./backend
docker build --secret id=ca,src=/path/to/company-ca.crt -t local-frontend ./frontend
docker compose --env-file .env -f deploy/local/compose.yaml up -d
```

บน PowerShell ตัวอย่าง path คือ `--secret id=ca,src="C:\\path\\company-ca.crt"` และใช้ขั้นตอนนี้เฉพาะเมื่อพบ error เรื่อง certificate เท่านั้น

## 3. สร้าง Admin สำหรับเครื่องนี้

```bash
docker compose --env-file .env -f deploy/local/compose.yaml exec backend python -m app.cli bootstrap-admin
```

สร้าง email และรหัสผ่านทดสอบของคุณเอง รหัสผ่านควรยาวอย่างน้อย 12 ตัวอักษร อย่าใช้รหัสผ่านของเครื่องจริงหรือส่งรหัสผ่านในแชต

## 4. เปิดและตรวจระบบ

- Dashboard: `https://localhost`
- API docs: `https://localhost/api/docs`
- Health check: `https://localhost/api/v1/health`

Caddy ใช้ certificate สำหรับ local จึงอาจมีคำเตือนใน browser ให้ยอมรับเฉพาะบนเครื่องทดสอบนี้ ห้ามเปิด port นี้ออก internet

```bash
curl -k https://localhost/api/v1/health
```

บน Windows ใช้ `curl.exe -k ...` หาก `curl` ถูก map ไปเป็น PowerShell command

## 5. ลำดับทดสอบแนะนำ

1. Login ด้วย Admin ที่สร้างไว้
2. สร้าง Hospital และตรวจรายการใน Hospital Draft
3. สร้าง Equipment แล้วอนุมัติตามลำดับ Hospital -> Equipment
4. สร้าง PM Plan และทดลอง Preview/Approve แผนรายปี
5. ตรวจ PM Slots และปฏิทิน
6. สร้าง Technician intake แล้วตรวจ queue/review
7. สร้างหรืออนุมัติ Appointment และทดลองยืนยันวันนัด/ขอเลื่อน
8. ตรวจ Appointment history และ Reports
9. ทดลอง Google/LINE operations แบบ mock และดู outbox/retry โดยยังไม่ใส่ credential จริง

ข้อควรจำ: `CONFIRMED` คือโรงพยาบาลยอมรับวันนัดล่วงหน้า ไม่ใช่สถานะทำงานเสร็จ ระบบไม่มี `COMPLETED`

## 6. หยุดและเปิดต่อ

```bash
docker compose --env-file .env -f deploy/local/compose.yaml stop
docker compose --env-file .env -f deploy/local/compose.yaml start
```

หากต้องลบ container แต่เก็บข้อมูลให้ใช้ `down` ได้ ส่วน `down -v` จะลบฐานข้อมูลทดสอบทั้งหมด ควรใช้เฉพาะเมื่อตั้งใจ reset เครื่อง:

```bash
docker compose --env-file .env -f deploy/local/compose.yaml down
```

## 7. สำรองข้อมูลก่อนย้ายไป local server

```bash
docker compose --env-file .env -f deploy/local/compose.yaml exec -T db pg_dump -U ba_chiller -d ba_chiller > backup.sql
```

เมื่อเตรียม server ใหม่แล้วจึง restore เข้า database ของ server นั้น:

```bash
cat backup.sql | docker compose --env-file .env -f deploy/local/compose.yaml exec -T db psql -U ba_chiller -d ba_chiller
```

ตรวจชื่อ project, database และ backup ให้ถูกต้องก่อน restore ทุกครั้ง เพราะคำสั่งนี้เขียนข้อมูลลงฐานเป้าหมาย

## ปัญหาที่พบบ่อย

- Port 80/443 ถูกใช้งาน: ปิด IIS/Apache/โปรแกรมที่ใช้ port หรือแก้ mapping ใน `deploy/local/compose.yaml` เป็น `8080:80` และ `8443:443` แล้วเปิด `https://localhost:8443`
- Backend ต่อ database ไม่ได้: ตรวจว่า URL ใช้ `@db:5432` ไม่ใช่ `@localhost:5432`
- Service ยังไม่ healthy: รอ migration แล้วดู `docker compose ... logs --tail=100 backend db`
- Browser เตือน certificate: ใช้เฉพาะ local และเข้า `https://localhost` ตามขั้นตอนด้านบน
- ห้ามใส่ LINE token, Google service-account JSON หรือ Gemini key ใน Git และอย่าเปิด integration จริงระหว่างการทดลองครั้งแรก

## ถ้าไม่ใช้ Docker Desktop (Windows)

วิธีนี้ต้องเปิด Backend, Frontend, Worker และ Scheduler แยกกันหลายหน้าต่าง โดยติดตั้ง Python, Node.js และ PostgreSQL จากลิงก์ด้านบนก่อน

### 1. ตั้งค่า PostgreSQL

ระหว่างติดตั้ง PostgreSQL สำหรับเครื่องทดสอบนี้ ให้ใช้ค่าดังนี้:

```text
Username: admin
Password: admin
Port: 5432
```

ค่าดังกล่าวใช้สำหรับ local notebook เท่านั้น ห้ามใช้บน local server จริงหรือ production

เปิด pgAdmin 4 > Query Tool แล้วสร้างฐานข้อมูล:

```sql
CREATE DATABASE ba_chiller OWNER admin;
```

ถ้า installer สร้าง user `admin` ให้แล้ว ไม่ต้องสร้าง user ซ้ำ หากยังไม่มี user ให้รัน:

```sql
CREATE USER admin WITH PASSWORD 'admin';
CREATE DATABASE ba_chiller OWNER admin;
```

### 2. ดาวน์โหลดโค้ดและตั้งค่า `.env`

```powershell
git clone https://github.com/02sxry/ba-chiller-service-pm.git
cd ba-chiller-service-pm
Copy-Item .env.example .env
```

แก้ค่าใน `.env` เป็นแบบติดตั้งตรงบน Windows:

```dotenv
APP_ENV=development
APP_HOST=localhost
SECRET_KEY=local-notebook-secret-key
POSTGRES_PASSWORD=admin
DATABASE_URL=postgresql+psycopg://admin:admin@localhost:5432/ba_chiller
DATABASE_URL_SYNC=postgresql+psycopg://admin:admin@localhost:5432/ba_chiller
FRONTEND_ORIGIN=http://localhost:5173
NOTIFICATIONS_ENABLED=false
NOTIFICATION_KILL_SWITCH=true
GOOGLE_USE_REAL_PROVIDER=false
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
GEMINI_API_KEY=
```

### 3. ติดตั้งและเปิด Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli bootstrap-admin
uvicorn app.main:app --reload
```

ถ้า PowerShell บล็อกการ activate ให้รันก่อนหนึ่งครั้งในหน้าต่างนั้น:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

เปิดทิ้งไว้ที่ `http://localhost:8000`

### 4. เปิด Frontend

เปิด PowerShell ใหม่:

```powershell
cd ba-chiller-service-pm\frontend
npm install
npm run dev
```

เปิดเว็บที่ `http://localhost:5173`

### 5. เปิด Worker และ Scheduler

เปิด PowerShell เพิ่มอีกสองหน้าต่าง แล้วรันคำสั่งต่อไปนี้ โดยต้อง activate `.venv` ทุกหน้าต่าง:

```powershell
cd ba-chiller-service-pm\backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

และอีกหน้าต่าง:

```powershell
cd ba-chiller-service-pm\backend
