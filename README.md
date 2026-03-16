# Object Detection App

แอปตรวจจับวัตถุ (YOLO + GUI) ที่ออกแบบให้เป็น **portable app ขนาดย่อม**  
ย้ายโฟลเดอร์ไปเครื่องไหนก็ได้ แล้วสั่งรันได้เลยทั้ง **macOS / Windows / Linux**

## จุดเด่น

- รันข้ามแพลตฟอร์มจากโค้ดชุดเดียว
- เปิดครั้งแรก: สร้าง virtual environment และติดตั้งไลบรารีให้อัตโนมัติ
- ครั้งถัดไป: เปิดแอปได้ทันที (ไม่ติดตั้งซ้ำถ้า `requirements.txt` ไม่เปลี่ยน)
- รองรับโมเดล `.pt` และ `.engine` ที่วางไว้ในโฟลเดอร์ `model/`
- เก็บผล `captures/` และ `csv_logs/` แยกเป็นระเบียบ

## วิธีทำงานแบบอัตโนมัติ (ครั้งแรก)

เมื่อรันแอปผ่าน launcher (`run_app.py` / `run_app.sh` / `run_app.bat`) ระบบจะ:

1. ตรวจสอบ Python เวอร์ชัน (ต้อง 3.10+)
2. สร้าง venv อัตโนมัติ (ใช้ `.venv` เป็นหลัก และรองรับ `venv` เดิมถ้ามี)
3. ติดตั้ง dependency จาก `requirements.txt`
4. เปิด `app.py`

ถ้าแก้ `requirements.txt` ภายหลัง ระบบจะติดตั้งอัปเดตให้อัตโนมัติรอบถัดไป

## ความต้องการระบบ

- Python 3.10 - 3.12 (แนะนำ)
- อินเทอร์เน็ตสำหรับรอบติดตั้งครั้งแรก

Linux บางเครื่องอาจต้องติดตั้งแพ็กเกจระบบเพิ่ม:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk libgl1 libglib2.0-0
```

## การรันแอป

### macOS / Linux

```bash
./run_app.sh
```

### Windows (Command Prompt)

```bat
run_app.bat
```

### ทุกระบบ (ทางเลือกกลาง)

```bash
python run_app.py
```

## โครงสร้างไฟล์สำคัญ

- `app.py` : ตัวแอป GUI ตรวจจับวัตถุ
- `run_app.py` : launcher อัตโนมัติ (สร้าง venv + install + run)
- `run_app.sh` : ตัวเรียกใช้งานสำหรับ macOS/Linux
- `run_app.bat` : ตัวเรียกใช้งานสำหรับ Windows
- `requirements.txt` : รายการไลบรารี
- `model/` : ไฟล์โมเดล AI (`.pt`, `.engine`)
- `captures/` : รูป snapshot และวิดีโอบันทึก
- `csv_logs/` : ไฟล์ log การตรวจจับ

## การใส่โมเดล

1. นำไฟล์โมเดล `.pt` หรือ `.engine` วางไว้ในโฟลเดอร์ `model/`
2. กด `Refresh Models` ในแอป
3. เลือกโมเดลจาก dropdown แล้วเริ่มตรวจจับ

## หมายเหตุการพกพา (Portable)

- ย้ายทั้งโฟลเดอร์โปรเจกต์ไปเครื่องใหม่ได้เลย
- ไม่ต้อง activate venv เอง
- ถ้าเครื่องปลายทางคนละ OS ตัว launcher จะสร้าง environment ที่เหมาะกับ OS นั้นให้อัตโนมัติ

## แก้ปัญหาเบื้องต้น

- กล้องไม่ขึ้น: ตรวจสิทธิ์กล้องของระบบปฏิบัติการ และลองเปลี่ยน camera index เป็น `0`, `1`, `2`
- เปิด GUI ไม่ได้บน Linux: ติดตั้ง `python3-tk` และ `libgl1` ตามด้านบน
- ติดตั้งแพ็กเกจไม่ผ่าน: ตรวจว่าใช้ Python 3.10+ และมีอินเทอร์เน็ต
