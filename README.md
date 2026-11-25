# BA_PMnotification

ระบบวางแผน PM และจัดการนัดหมายงาน Chiller สำหรับโรงพยาบาล โดยใช้ SQL Server เป็นฐานข้อมูลหลักและ SSMS เป็นเครื่องมือจัดการฐานข้อมูล ส่วน Google Sheets เป็นช่องทาง staging/reporting เท่านั้น

> `CONFIRMED` หมายถึงโรงพยาบาลยอมรับวันนัดล่วงหน้า ระบบนี้ไม่มีสถานะ `COMPLETED` และไม่อนุมานว่างานบริการเสร็จแล้ว

## เริ่มระบบสำหรับพัฒนา

ต้องมี SQL Server, Microsoft ODBC Driver 18, Python 3.12+ และ Node.js 24+

```bash
cd backend
# ตั้ง DATABASE_URL ใน .env ให้ชี้ SQL Server/BA_PMnotification ก่อนรันคำสั่งต่อไปนี้
uv sync --frozen
alembic upgrade head
uvicorn app.main:app --reload
```

เปิดอีก terminal

```bash
cd frontend
npm install
npm run dev
```

API docs อยู่ที่ `http://localhost:8000/api/docs` และเว็บอยู่ที่ `http://localhost:5173`

สร้าง Admin คนแรกหลัง migration โดยใช้ User ID `admin` และรหัสผ่าน `admin` ได้เฉพาะ local development

```bash
python -m app.cli bootstrap-admin
```

ถ้ารันด้วย production Compose ให้สร้างจาก backend container:

```bash
docker compose --env-file .env -f deploy/local/compose.yaml exec backend python -m app.cli bootstrap-admin
```

## ทดสอบ

ถ้าต้องการทดลองทั้งระบบบนโน้ตบุ๊กด้วย Docker Desktop ให้ทำตาม [คู่มือทดลองบนโน้ตบุ๊ก](docs/LAPTOP_TEST.md)

```bash
cd backend
pytest -q
ruff check app tests alembic

cd ../frontend
npm run build
```

ระบบปิดการส่ง notification จริงไว้โดยค่าเริ่มต้น และใช้ mock LINE/Google adapter เมื่อไม่มี credentials ดูรายละเอียดใน [คู่มือ Integration](docs/INTEGRATIONS.md) และ [รายงานการทดสอบ](TEST_REPORT.md)

ถ้าบริษัทกำหนดใช้ SQL Server/SSMS ให้ทำตาม [คู่มือ SQL Server](docs/SQL_SERVER.md) ก่อนย้ายข้อมูลจริง

## โครงสร้าง

- `backend/` FastAPI, SQLAlchemy, Alembic, worker และ tests
- `frontend/` React, TypeScript, Vite และ Thai dashboard
- `deploy/local/` Docker Compose สำหรับ local server, Caddy และ persistent volumes
- `docs/` สถาปัตยกรรม กฎธุรกิจ การติดตั้ง และ security design
- `scripts/` bootstrap Admin และสร้าง Google workbook template

