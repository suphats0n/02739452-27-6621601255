# ผลการตรวจระบบเดิม — 23 ตุลาคม 2026

ลำดับที่ 27 · รหัสนิสิต 6621601255

Repository: https://github.com/suphats0n/02739452-27-6621601255

## ผลที่ตรวจแล้ว

- ตรวจไฟล์ source, Compose, Dockerfiles, schema, tests และเอกสารในโปรเจกต์เดิม
- Python compileall ผ่าน และ local `pip check`: No broken requirements found
- `scripts/test_transform.py`: 4 tests ผ่าน
- `scripts/test_pipeline.py`: FreeToGame 353, CheapShark 180, Wikipedia 171 records; หลัง deduplicate 618 source records / 586 games; quality ผ่าน
- ทดสอบ source-failure tolerance และ quality accept/reject ผ่าน
- PostgreSQL ทั้งสอง service healthy
- `scripts/test_database.py`: insert, repeat และ update ผ่านใน games, raw_games และ game_offers; จำนวนแถวคงที่เมื่อรันซ้ำ/อัปเดต และตรวจค่าที่เปลี่ยนจากฐานข้อมูลจริงแล้ว; ลบเฉพาะ fixture ที่สคริปต์สร้างเองหลังทดสอบ

## ปัญหาที่พบและแก้ไข

1. Docker API: permission denied ใน sandbox — ใช้สิทธิ์ที่ระบบอนุญาตเพื่อเรียก Docker Desktop
2. Airflow scheduler healthcheck ใช้ CMD กับตัวแปร HOSTNAME ซึ่งไม่ขยายค่า — เปลี่ยนเป็น CMD-SHELL
3. ไม่มี .dockerignore — เพิ่มเพื่อไม่ส่ง .venv, .git และ .env เข้า build context
4. Task สรุปสถานะ ALL_DONE อาจทำให้ DAG สำเร็จแม้โหลดไม่ผ่าน — บันทึกสถานะก่อน raise AirflowException เมื่อ pipeline ล้มเหลว
5. Docker Hub ดาวน์โหลด apache/airflow:2.10.5-python3.11 timeout ซ้ำ — ใช้ build argument กับ base apache/airflow:2.10.4 ที่มีอยู่ แล้วติดตั้ง Airflow 2.10.5
6. GitHub ใน sandbox เชื่อม proxy 127.0.0.1:9 ไม่ได้ — ตรวจ remote ด้วยสิทธิ์เครือข่ายที่ได้รับ; remote เข้าถึงได้และยังไม่มี refs ตอนตรวจ
7. Dashboard เริ่มต้นใช้ช่วงราคาเต็มเป็นเงื่อนไข SQL ทำให้ซ่อนเกมที่ไม่มีราคา — กรองราคาเฉพาะเมื่อปรับ slider จากค่าเริ่มต้น; หน้าแรกแสดงเกมทั้งหมด
8. Airflow build เดิมติดตั้ง dependencies ของ Dashboard ทำให้ pandas ขัดกับ Google/Snowflake providers และอัปเดต fsspec ไม่ตรง gcsfs — แยก requirements-airflow.txt ติดตั้งเฉพาะที่ ETL ใช้ และเพิ่ม pip check ใน build
9. pandas เตือนเมื่ออ่านผ่าน psycopg2 connection — ใช้ parameterized cursor และแปลงผลเป็น DataFrame โดยตรง

## การเริ่มระบบเมื่อ Docker Hub timeout

เครื่องนี้มี base image apache/airflow:2.10.4 (Python 3.12) อยู่แล้ว:

```powershell
docker compose build --build-arg AIRFLOW_BASE_IMAGE=apache/airflow:2.10.4 airflow-init airflow-webserver airflow-scheduler
docker compose up -d --no-build
```

Default Dockerfile ยังคงใช้ apache/airflow:2.10.5-python3.11; ทั้งสองเส้นทางติดตั้ง Airflow 2.10.5

## ผล runtime

- โหลดข้อมูลจริงจาก 3 sources ผ่าน Dashboard container: 586 games, 618 raw records, 180 offers
- raw records แยกตามแหล่ง: FreeToGame 353, CheapShark 94 (180 offers จากหลายร้าน), Wikipedia 171
- โหลด transformed dataset เดิมซ้ำ: จำนวนแถวทั้งสามตารางเท่าเดิมทั้งหมด
- Dashboard health HTTP 200; dependencies ใน container ผ่าน pip check
- Streamlit AppTest ผ่านการ render metrics/กราฟ/ตาราง, genre/source/search/price filters และผลค้นหาว่าง
- Airflow 2.10.5 build และ runtime pip check ผ่าน; list-import-errors: No data found
- ทั้ง 5 services ที่ทำงานต่อเนื่อง healthy; airflow-init ออกด้วย exit code 0 ตามปกติ
- Scheduler ทำงานจริง 2 runs สำเร็จ:
  - scheduled__2026-10-22T02:00:00+00:00: ทำงานจริงวันที่ 23 ต.ค. เวลา 14:07:53–14:08:32 น. (Asia/Bangkok)
  - exam_verification_20261023: วันที่ 23 ต.ค. เวลา 14:08:32–14:08:47 น. (Asia/Bangkok)
- แต่ละ run ดึงรวม 704 records, โหลดหลัง deduplicate 618 records, failed_sources=0, quality_passed=true
- Manual run: extract ทั้งสาม, transform, quality, branch, load และ record_pipeline_status เป็น success; quality_rejected เป็น skipped ตาม branch ที่ผ่าน
- PostgreSQL หลัง DAG สอง runs: 586 games / 618 raw records / 180 offers คงเดิม
- Airflow host health: metadatabase และ scheduler healthy; login ด้วยบัญชี .env และหน้า DAG Grid ตอบ HTTP 200
- Dashboard ผ่าน host port 8502 ตอบ HTTP 200; AppTest หลังมีประวัติ pipeline จริงผ่านซ้ำแล้ว
- ตรวจไฟล์ที่เตรียมเข้า Git ไม่พบค่ารหัสผ่าน/secret จริงจาก .env; .env และ .venv ถูก ignore

## เปิดระบบและส่ง GitHub

- Airflow: http://localhost:8191 — บัญชีอยู่ใน .env
- Dashboard: http://localhost:8502
- PostgreSQL: localhost:5453
- ระบบเปิดทิ้งไว้พร้อมตรวจสอบ; ถ้า containers หยุด ใช้ `docker compose up -d --no-build`
- Remote origin ตั้งแล้ว; หลัง commit ใช้ `git push -u origin main`
- ยังไม่ได้ push, สร้าง PDF หรือบันทึก screenshots; ภาพในรายงานต้องบันทึกจาก UI จริง
