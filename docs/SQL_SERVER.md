# ใช้ SQL Server / SSMS เป็นฐานข้อมูลของระบบ

BA_PMnotification ใช้ SQL Server เป็นฐานข้อมูลหลักเพียงตัวเดียว ผ่าน SQLAlchemy และ ODBC Driver 18 ส่วน SSMS ใช้สำหรับสร้างฐานข้อมูล ตรวจตาราง และสำรองข้อมูล

## 1. เตรียม SQL Server

ให้ผู้ดูแล SQL Server สร้างฐานข้อมูลและ login สำหรับแอปใน SSMS ตัวอย่างนี้ใช้ชื่อฐานข้อมูล `BA_PMnotification` และ login `BA_PMnotification_app`:

```sql
CREATE DATABASE [BA_PMnotification];
GO

USE [BA_PMnotification];
GO

CREATE LOGIN [BA_PMnotification_app] WITH PASSWORD = 'เปลี่ยนเป็นรหัสผ่านจริงที่แข็งแรง';
GO

CREATE USER [BA_PMnotification_app] FOR LOGIN [BA_PMnotification_app];
ALTER ROLE db_datareader ADD MEMBER [BA_PMnotification_app];
ALTER ROLE db_datawriter ADD MEMBER [BA_PMnotification_app];
ALTER ROLE db_ddladmin ADD MEMBER [BA_PMnotification_app];
GO
```

ทำขั้นตอนนี้ด้วยบัญชีผู้ดูแลเท่านั้น และไม่ใส่รหัสผ่านจริงลง Git หรือส่งในแชต

## 2. ติดตั้ง driver และ Python package

บนเครื่องที่รัน Backend ต้องติดตั้ง **Microsoft ODBC Driver 18 for SQL Server** ให้ตรงกับ Windows/Linux และต้องติดตั้งส่วนเสริม Python ของโปรเจกต์:

```bash
cd backend
uv sync --frozen
```

ถ้าใช้ `pip` แทน `uv`:

```bash
pip install -e "."
```

## 3. ตั้งค่า `DATABASE_URL`

ใส่ในไฟล์ `.env` ของ Backend ตัวอย่าง SQL Authentication:

```dotenv
DATABASE_URL=mssql+pyodbc://BA_PMnotification_app:รหัสผ่านที่เข้ารหัสแล้ว@SQLSERVER_HOST:1433/BA_PMnotification?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

ถ้ารหัสผ่านมีอักขระพิเศษ เช่น `@`, `#`, `/` ต้อง URL-encode ก่อน หรือใช้รูปแบบ `odbc_connect` ตามเอกสาร SQLAlchemy สำหรับ pyodbc

ถ้าองค์กรใช้ Windows Authentication ให้ใช้รูปแบบนี้แทน:

```dotenv
DATABASE_URL=mssql+pyodbc://@SQLSERVER_HOST/BA_PMnotification?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes
```

`SQLSERVER_HOST` อาจเป็น `SERVERNAME`, `SERVERNAME\\INSTANCE` หรือ `SERVERNAME,1433` ตามค่าที่องค์กรกำหนด

## 4. สร้างตารางของระบบ

รันจากโฟลเดอร์ `backend` โดยใช้ environment เดียวกับที่ติดตั้ง package:

```bash
alembic upgrade head
```

จากนั้นสร้างบัญชีผู้ดูแล:

```bash
python -m app.cli ensure-admin
```

คำสั่ง migration ใช้ชนิดข้อมูลกลางของ SQLAlchemy ดังนั้น UUID จะถูกสร้างเป็น `UNIQUEIDENTIFIER` และข้อมูล JSON จะถูกเก็บเป็น `NVARCHAR(MAX)` บน SQL Server

## 5. ตรวจสอบก่อนย้ายใช้งานจริง

1. เปิด `/api/v1/health` ต้องได้ `database: ok`
2. เข้าระบบด้วย `admin/admin` เฉพาะช่วง local test แล้วเปลี่ยนรหัสผ่านก่อนใช้งานจริง
3. สร้างโรงพยาบาลและอุปกรณ์ทดสอบ 1 รายการจากหน้าเว็บ
4. ตรวจตาราง `users`, `hospitals`, `equipment` ใน SSMS
5. ทดสอบสร้างแผน PM และยกเลิก/Archive อุปกรณ์
6. ทำ backup SQL Server ก่อนนำข้อมูลจริงหรือเปิด LINE

ระบบนี้จะอ่านและบันทึกข้อมูลจาก SQL Server/BA_PMnotification เท่านั้น
