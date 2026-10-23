# รายงานสรุปผลสอบ (ไม่เกิน 3 หน้า)

ไฟล์ PDF เป้าหมาย: `27_6621601255_summary.pdf`

## สถานะการจัดทำ

- รหัสนิสิต: `6621601255`
- ลำดับที่: `27`
- GitHub Repository: https://github.com/suphats0n/02739452-27-6621601255
- ผลทดสอบที่บันทึกจริง: [verification.md](verification.md)
- ผลที่ตรวจแล้ว: Compose healthy, Airflow DAG success 2 runs, PostgreSQL 586 เกม, Dashboard และ UPSERT ผ่าน; รายละเอียดใน verification.md
- ยังไม่แนบภาพผลทดสอบจริง: บันทึกภาพตามรายการด้านล่างก่อนส่ง

## หน้า 1 — ระบบและ Architecture

ชื่อระบบ: PC Game Analytics — ระบบรวบรวมและวิเคราะห์ข้อมูลเกม PC ฟรีและเกมลดราคา

แหล่งข้อมูลจริง: FreeToGame API, CheapShark API และ Wikipedia table scraping (ตรวจ robots.txt ก่อนดึง HTML) ข้อมูลถูก normalize, ตรวจคุณภาพ และ UPSERT ลง PostgreSQL ด้วย Apache Airflow TaskGroup ก่อนอ่านโดยตรงจาก Streamlit Dashboard

ภาพ Architecture: `../README.md` ส่วน Architecture

หลักฐานภาพที่ต้องแนบ:

1. Airflow Graph View: เปิด `http://localhost:8191`, เลือก DAG `pc_game_analytics_pipeline`, แสดง task group และผล run จริง
2. Airflow Grid View: แสดงสถานะ task ของ run เดียวกัน
3. Dashboard: เปิด `http://localhost:8502` หลัง pipeline โหลดข้อมูลจริง

บันทึกภาพจริงลงโฟลเดอร์ `screenshots/` โดยไม่แก้ไขภาพให้ดูเหมือนผลการทดสอบที่ไม่เกิดขึ้น

## หน้า 2 — ปัญหาและการทดสอบ

กรอกอย่างน้อย 2 ปัญหาที่พบจริง โดยแต่ละรายการระบุ:

| ปัญหา/อาการจริง | วิธีตรวจหาสาเหตุ | วิธีแก้ | ผลทดสอบจริง |
|---|---|---|---|
| Docker Hub ดาวน์โหลด Airflow timeout | build/pull logs: context deadline exceeded | ใช้ base image ในเครื่อง แล้วติดตั้ง Airflow 2.10.5 | build และ runtime pip check ผ่าน; DAG success |
| Dashboard ซ่อนเกมที่ไม่มีราคาเมื่อเปิดหน้าแรก | AppTest ตรวจจำนวนเกมเทียบ PostgreSQL | ใช้เงื่อนไขราคาเฉพาะเมื่อปรับ slider | แสดง 586 เกม; filters/empty results ผ่าน |

ไม่กรอกผล PASS หากยังไม่ได้ทดสอบส่วนนั้น

## หน้า 3 — เวลาและผลลัพธ์

| เวลา | ลำดับความสำคัญ/กิจกรรม | ผลจริง |
|---|---|---|
| `[กรอก]` | P0: Docker, PostgreSQL, Airflow, 1 source, dashboard | `[กรอก]` |
| `[กรอก]` | P1: 2 sources, TaskGroup, UPSERT, filters | `[กรอก]` |
| `[กรอก]` | P2–P3: scraping, resilience, quality, status | `[กรอก]` |
| `[กรอก]` | P4: documentation, screenshots, report | `[กรอก]` |

งานที่ตัดออกและเหตุผล: `[กรอกเฉพาะเมื่อมีการตัดงานจริง]`

สรุปผลลัพธ์จริง: DAG ผ่าน scheduler 2 runs, ทุก source สำเร็จ, quality ผ่าน, ฐานข้อมูลมี 586 games / 618 raw records / 180 offers; UPSERT ซ้ำและเปลี่ยนค่าผ่าน; Dashboard และ Airflow login/Grid ตอบ HTTP 200
