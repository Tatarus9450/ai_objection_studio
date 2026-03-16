# AI ตรวจจับขนม

เว็บแอปสำหรับตรวจจับขนมจากกล้องแบบสด โดยใช้โมเดล `kanom_v2.pt` ที่รันในเครื่องของผู้ใช้เอง

จุดสำคัญของโปรเจกต์นี้คือ:
- ใช้งานผ่าน browser
- รองรับ macOS / Windows / Linux
- เปิดครั้งแรกแล้วสร้าง virtual environment และติดตั้งไลบรารีให้อัตโนมัติ
- ล็อกโมเดลไว้ที่ `model/kanom_v2.pt` เท่านั้น
- ใช้เฉพาะการตรวจจับผ่านกล้องสด ไม่มีโหมดอัปโหลดภาพหรือวิดีโอ

## ความสามารถหลัก

- ตรวจจับขนมจาก webcam แบบ real-time
- แสดง `Camera Input` และ `Annotated Output` แยกชัดเจนบนหน้าเว็บ
- ปรับ `Confidence`, `IoU`, `Resolution`, และ `Class Filter` ได้
- แสดง `Webcam FPS`
- แสดง `Live Summary` ของวัตถุที่ตรวจพบ
- มี `Quick Tips` ในหน้าเว็บสำหรับช่วยตั้งกล้องให้ได้ผลลัพธ์ดีขึ้น
- เปิดใช้งานได้แบบ portable โดยไม่ต้องติดตั้ง dependency ด้วยมือทุกครั้ง

## สถานะปัจจุบันของระบบ

- โมเดลที่ใช้งานจริง: `model/kanom_v2.pt`
- ไม่สามารถเปลี่ยนโมเดลจากหน้าเว็บได้
- ถ้าไม่พบไฟล์ `kanom_v2.pt` โปรแกรมจะไม่เริ่มทำงาน
- แอปประมวลผลในเครื่อง ไม่อัปโหลดภาพไป cloud

## ความต้องการของระบบ

- Python `3.10` หรือใหม่กว่า
- ไฟล์โมเดล `model/kanom_v2.pt`
- Browser ที่รองรับ `getUserMedia()` เช่น Chrome, Edge, Safari

## วิธีเริ่มใช้งาน

### 1. วางโมเดล

ตรวจสอบให้มีไฟล์นี้อยู่ในโฟลเดอร์ `model/`

```text
model/kanom_v2.pt
```

### 2. เปิดแอป

macOS / Linux:

```bash
./run_app.sh
```

Windows:

```bat
run_app.bat
```

ทุกระบบ:

```bash
python run_app.py
```

## สิ่งที่ launcher ทำให้อัตโนมัติ

ไฟล์ `run_app.py` จะทำงานดังนี้:

1. ตรวจสอบ Python version
2. หา `.venv` หรือ `venv` ที่ใช้งานได้
3. ถ้ายังไม่มี จะสร้าง virtual environment ใหม่
4. ติดตั้งหรืออัปเดต dependency จาก `requirements.txt`
5. ตรวจว่ามี `model/kanom_v2.pt`
6. เปิด web app ผ่าน `app.py`

ถ้า browser ไม่เปิดเอง ให้ใช้ URL ที่แสดงใน terminal เช่น `http://127.0.0.1:8000`

## วิธีใช้งานบนหน้าเว็บ

1. เปิดแอป
2. อนุญาตสิทธิ์เข้าถึงกล้องใน browser
3. ปรับค่า `Confidence`, `IoU`, `Resolution`, หรือ `Class Filter` ตามต้องการ
4. กด `Start Detection`
5. ดูภาพจากกล้องใน `Camera Input`
6. ดูผลกรอบตรวจจับใน `Annotated Output`
7. ดูจำนวนวัตถุจาก `Live Summary`

## คำอธิบายตัวควบคุม

- `Confidence`: ค่าความมั่นใจขั้นต่ำของผลตรวจจับ
- `IoU`: ค่าควบคุมการรวมกรอบซ้ำ
- `Resolution`: ความละเอียดที่ใช้ใน live detection
- `Class Filter`: ระบุ class id ที่ต้องการ เช่น `0,1,2`

## โครงสร้างไฟล์หลัก

- `app.py` : Flask server และ endpoint `/api/detect/frame`
- `run_app.py` : launcher แบบ portable
- `run_app.sh` : ตัวเปิดสำหรับ macOS / Linux
- `run_app.bat` : ตัวเปิดสำหรับ Windows
- `services/model_runtime.py` : โหลดโมเดลและรัน inference
- `services/live_detection.py` : decode frame, detect, encode output
- `templates/index.html` : หน้าเว็บหลัก
- `static/app.js` : logic ฝั่ง browser
- `static/styles.css` : layout และสไตล์ของ UI
- `model/` : โฟลเดอร์เก็บโมเดล

## ปัญหาที่พบบ่อย

### ไม่พบโมเดล

อาการ:
- โปรแกรมแจ้งว่าไม่พบ `kanom_v2.pt`

วิธีแก้:
- วางไฟล์ `kanom_v2.pt` ไว้ในโฟลเดอร์ `model/`

### Browser เปิดไม่ขึ้นอัตโนมัติ

อาการ:
- โปรแกรมรันแล้วแต่ไม่เปิดหน้าเว็บเอง

วิธีแก้:
- เปิด URL ที่แสดงใน terminal ด้วยตัวเอง

### กล้องไม่ทำงาน

อาการ:
- กด `Start Detection` แล้วไม่ขึ้นภาพ

วิธีแก้:
- อนุญาตสิทธิ์กล้องใน browser
- ปิดแอปอื่นที่กำลังใช้งาน webcam
- รีเฟรชหน้าเว็บแล้วลองใหม่

### FPS ต่ำ

สิ่งที่ควรรู้:
- คอขวดหลักมักอยู่ที่การรันโมเดลบน CPU
- แม้เลือก `640` แล้ว FPS ยังอาจต่ำได้ ขึ้นกับเครื่อง

วิธีปรับปรุง:
1. ลด `Resolution` เป็น `320`
2. ปิดโปรแกรมอื่นที่ใช้ CPU/GPU
3. ใช้เครื่องที่รองรับ `CUDA` หรือ `MPS` ถ้ามี
4. ใช้แสงที่ดีและจัดวัตถุให้อยู่ชัดในเฟรม

## หมายเหตุ

- โปรเจกต์นี้ออกแบบมาเป็น `live detection workspace`
- ไม่มี flow สำหรับ image upload หรือ video upload
- README นี้อ้างอิงจากโค้ดสถานะปัจจุบันของโปรเจกต์
