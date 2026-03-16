# Vision Deck

Vision Deck คือ web app สำหรับ Object Detection ที่รันในเครื่องตัวเองได้เลย  
เปิดผ่าน browser แต่ประมวลผลด้วย Python + YOLO ในเครื่องเดียวกัน

## ความสามารถหลัก

- Live webcam detection ผ่านหน้าเว็บ
- อัปโหลดภาพเพื่อตรวจจับและดูภาพ annotated
- อัปโหลดวิดีโอเพื่อประมวลผลทั้งไฟล์และดาวน์โหลดผลลัพธ์
- เลือกโมเดลจากโฟลเดอร์ `model/`
- ปรับ `confidence`, `IoU`, `resolution`, และ `class filter`
- บันทึก `CSV log`
- เซฟ `snapshot`
- อัด `recording` จาก live annotated canvas

## วิธีรัน

### macOS / Linux

```bash
./run_app.sh
```

### Windows

```bat
run_app.bat
```

### ทุกระบบ

```bash
python run_app.py
```

เมื่อเปิดครั้งแรก launcher จะ:

1. สร้าง virtual environment ให้อัตโนมัติ
2. ติดตั้งไลบรารีจาก `requirements.txt`
3. เปิด web app ให้อัตโนมัติเมื่อเครื่องมี desktop session

ถ้า browser ไม่เปิดเอง ให้เข้า `http://127.0.0.1:8000` หรือพอร์ตถัดไปที่โปรแกรมแสดงใน terminal

## โครงสร้างสำคัญ

- `app.py` : Flask web server
- `detector_service.py` : logic ตรวจจับและจัดการไฟล์ output
- `templates/` : HTML
- `static/` : CSS และ JavaScript
- `model/` : โมเดล `.pt` หรือ `.engine`
- `captures/` : snapshot, recording, processed video
- `csv_logs/` : ไฟล์ CSV

## การใส่โมเดล

ใส่ไฟล์โมเดลไว้ในโฟลเดอร์ `model/` แล้วกด `Refresh Models` บนหน้าเว็บ

## หมายเหตุ

- ถ้าใช้ Live Camera ต้องอนุญาตสิทธิ์กล้องใน browser
- output runtime จะถูกเก็บไว้ใน `captures/` และ `csv_logs/`
- ไฟล์โมเดลไม่ถูก track ใน Git ตาม `.gitignore`
