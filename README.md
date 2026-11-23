# BA Chiller Service & PM Assistant

ระบบวางแผน PM และจัดการนัดหมายงาน Chiller สำหรับโรงพยาบาล โดย PostgreSQL เป็นแหล่งข้อมูลจริง และ Google Sheets เป็นช่องทาง staging/reporting เท่านั้น

> `CONFIRMED` หมายถึงโรงพยาบาลยอมรับวันนัดล่วงหน้า ระบบนี้ไม่มีสถานะ `COMPLETED` และไม่อนุมานว่างานบริการเสร็จแล้ว

## เริ่มระบบสำหรับพัฒนา

ต้องมี Docker, Python 3.12+ และ Node.js 24+

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql+psycopg://ba_chiller:ba_chiller@localhost:55432/ba_chiller alembic upgrade head
DATABASE_URL=postgresql+psycopg://ba_chiller:ba_chiller@localhost:55432/ba_chiller uvicorn app.main:app --reload
```

เปิดอีก terminal

```bash
cd frontend
npm install
npm run dev
```

API docs อยู่ที่ `http://localhost:8000/api/docs` และเว็บอยู่ที่ `http://localhost:5173`

สร้าง Admin คนแรกหลัง migration

```bash
DATABASE_URL=postgresql+psycopg://ba_chiller:ba_chiller@localhost:55432/ba_chiller python scripts/bootstrap_admin.py
```

## ทดสอบ

```bash
cd backend
DATABASE_URL=postgresql+psycopg://ba_chiller:ba_chiller@localhost:55432/ba_chiller pytest -q
ruff check app tests alembic

cd ../frontend
npm run build
```

ระบบปิดการส่ง notification จริงไว้โดยค่าเริ่มต้น และใช้ mock LINE/Google adapter เมื่อไม่มี credentials ดูรายละเอียดใน [คู่มือ Integration](docs/INTEGRATIONS.md) และ [รายงานการทดสอบ](TEST_REPORT.md)

## โครงสร้าง

- `backend/` FastAPI, SQLAlchemy, Alembic, worker และ tests
- `frontend/` React, TypeScript, Vite และ Thai dashboard
- `deploy/local/` Docker Compose สำหรับ local server, Caddy และ persistent volumes
- `docs/` สถาปัตยกรรม กฎธุรกิจ การติดตั้ง และ security design
- `scripts/` bootstrap Admin และสร้าง Google workbook template

