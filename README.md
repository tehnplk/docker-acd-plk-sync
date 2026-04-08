# ACD PLK Sync

โปรแกรม sync ข้อมูลจาก HOSxP ไปยัง accident web app แบบรันใน Docker

## หน้าที่ของโปรแกรม

- อ่านผล query จากฐานข้อมูลต้นทางด้วยไฟล์ `mysql_hosxp_acd_query.sql` หรือ `postgres_hosxp_acd_query.sql`
- แปลงข้อมูลแต่ละแถวให้เป็น payload ของ `patient` API
- ส่งข้อมูลไปที่ `/api/patient`
- เมื่อ container เริ่มทำงาน จะ sync ทันที 1 รอบ
- จากนั้นจะรันซ้ำทุก 30 นาทีด้วย `cron`
- บันทึก log แบบสั้นลงไฟล์ `sync.log`

## ไฟล์ที่เกี่ยวข้อง

- `plk-acd-sync.py` - สคริปต์หลักสำหรับ sync
- `mysql_hosxp_acd_query.sql` - query สำหรับ MySQL
- `postgres_hosxp_acd_query.sql` - query สำหรับ PostgreSQL
- `.env` - ค่าตั้งค่าที่ใช้ตอนรันจริง
- `compose.yml` - นิยามการรัน container
- `Dockerfile` - ขั้นตอน build image
- `run-sync.sh` - wrapper สำหรับรัน sync และเขียน log
- `docker-entrypoint.sh` - สั่ง sync 1 รอบตอน start แล้วค่อยเปิด cron

## การตั้งค่า

แก้ไฟล์ `.env` ก่อนเริ่มใช้งาน

ตัวอย่าง:

```env
# Database type: choose only "mysql" or "postgres"
DB_TYPE=mysql

# Source database connection
DB_HOST=host.docker.internal
DB_PORT=3306
DB_USER=root
DB_PASSWORD=112233
DB_NAME=hos11253

# Patient API target
API_URL=https://accident.plkhealth.go.th/api/patient
SECRET_KEY=accident-patient-jwt-2026-plk
```

หมายเหตุ:

- `DB_TYPE` ต้องเป็น `mysql` หรือ `postgres`
- `API_URL` ควรเป็น endpoint เต็มของ patient API
- `DB_HOST=host.docker.internal` ใช้ให้ container มองเห็นฐานข้อมูลบนเครื่อง host ของ Windows

## วิธี Build และ Run

รันจากโฟลเดอร์รากของโปรเจกต์:

```powershell
cd docker-acd-plk-sync
docker compose up -d --build
```

คำสั่งนี้จะ:

- build image ใหม่
- สร้าง container ชื่อ `acd-plk-sync`
- sync ทันที 1 รอบตอน container start
- เปิด `cron` ให้ทำงานต่อใน container

## ตรวจสอบสถานะ

```powershell
docker ps --filter "name=acd-plk-sync"
```

## ดู log

```powershell
Get-Content docker-acd-plk-sync\sync.log -Tail 20
```

รูปแบบ log จะมีแค่:

- `[datetime] sync start (N cases)`
- `[datetime] sync end (N cases added)`
- `[datetime] err (message)`

## เมื่อแก้ไฟล์แล้วต้อง rebuild

ถ้าแก้ไฟล์เหล่านี้:

- `plk-acd-sync.py`
- `*.sql`
- `.env`
- `run-sync.sh`
- `docker-entrypoint.sh`
- `Dockerfile`

ให้ rebuild container ใหม่ด้วย:

```powershell
cd docker-acd-plk-sync
docker compose up -d --build
```

## หยุด container

```powershell
cd docker-acd-plk-sync
docker compose down
```

## ตารางเวลา Cron

container นี้ตั้งค่าไว้ดังนี้:

- sync ทันที 1 รอบตอนเริ่มต้น
- หลังจากนั้น sync ทุก 30 นาที

ตารางเวลา cron อยู่ในไฟล์ `docker-acd-plk-sync/crontab`
