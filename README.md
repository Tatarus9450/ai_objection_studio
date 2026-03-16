# AI ตรวจจับขนม และ คิดเงิน

เว็บแอปสำหรับตรวจจับขนมจากกล้องแบบสดด้วย AI และสรุปยอดค่าสินค้าจากจำนวนที่ตรวจจับได้ในเฟรมปัจจุบัน

ระบบนี้ออกแบบให้ใช้งานแบบ portable:
- รันได้บน macOS / Windows / Linux
- เปิดครั้งแรกแล้วสร้าง virtual environment และติดตั้งไลบรารีให้อัตโนมัติ
- ใช้งานผ่าน browser
- ใช้โมเดล `model/kanom_v2.pt` แบบล็อกตาย

## ความสามารถหลัก

- ตรวจจับขนมจาก webcam แบบ real-time
- แสดง `Camera Input` และ `Annotated Output`
- ปรับ `Confidence`, `IoU`, `Resolution`, และ `Class Filter`
- แสดง `Webcam FPS`
- แสดง `Live Summary` ของวัตถุที่ตรวจจับได้
- แสดงหน้าต่าง `คิดเงินอัตโนมัติ` จากจำนวนสินค้าที่ AI พบ
- มี `Quick Tips` ช่วยแนะนำการจัดกล้องและวางสินค้า

## โมเดลที่ใช้

ระบบนี้ใช้โมเดล:

```text
model/kanom_v2.pt
```

ข้อกำหนด:
- ต้องมีไฟล์ `kanom_v2.pt` อยู่ในโฟลเดอร์ `model/`
- ไม่สามารถเปลี่ยนโมเดลจากหน้าเว็บได้
- ถ้าไม่พบไฟล์นี้ แอปจะไม่เริ่มทำงาน

## ราคาสินค้าที่ใช้คำนวณ

- `choco_pie` = 5 บาท
- `euro_cake` = 5 บาท
- `frit_c` = 5 บาท
- `jolly_cola` = 12 บาท
- `yumyum` = 4 บาท

ในหน้าเว็บจะแสดง:
- จำนวนสินค้าทั้งหมดที่นับได้
- ยอดรวมสุทธิเป็นเงินบาท

## ความต้องการของระบบ

- Python `3.10` หรือใหม่กว่า
- Browser ที่รองรับ `getUserMedia()` เช่น Chrome, Edge, Safari
- ไฟล์โมเดล `model/kanom_v2.pt`

## วิธีเปิดใช้งาน

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

## สิ่งที่ระบบติดตั้งอัตโนมัติให้

เมื่อรัน `run_app.py` ระบบจะ:

1. ตรวจสอบ Python version
2. เลือกใช้ `.venv` หรือ `venv` ที่ใช้งานได้
3. ถ้ายังไม่มี จะสร้าง virtual environment ใหม่
4. ติดตั้งหรืออัปเดต dependency จาก `requirements.txt`
5. ตรวจสอบว่าไฟล์ `model/kanom_v2.pt` มีอยู่จริง
6. เปิด web app ผ่าน `app.py`

ถ้า browser ไม่เปิดเอง ให้ใช้ URL ที่แสดงใน terminal เช่น:

```text
http://127.0.0.1:8000
```

## วิธีใช้งานบนหน้าเว็บ

1. เปิดแอป
2. อนุญาตสิทธิ์เข้าถึงกล้องใน browser
3. ปรับค่า `Confidence`, `IoU`, `Resolution`, หรือ `Class Filter`
4. กด `Start Detection`
5. ดูภาพจริงจากกล้องใน `Camera Input`
6. ดูผลกรอบตรวจจับใน `Annotated Output`
7. ดูรายการวัตถุใน `Live Summary`
8. ดูจำนวนชิ้นและยอดรวมใน `คิดเงินอัตโนมัติ`

## คำอธิบายส่วนต่าง ๆ บนหน้าเว็บ

- `Control Panel`
  ใช้ปรับค่าที่มีผลกับ live detection

- `Webcam FPS`
  แสดงอัตราเฟรมที่หน้าเว็บประมวลผลได้ในขณะนั้น

- `Live Summary`
  แสดงชื่อคลาสและจำนวนที่ตรวจจับได้จากเฟรมล่าสุด

- `คิดเงินอัตโนมัติ`
  สรุปรายการสินค้า จำนวนชิ้นทั้งหมด และยอดรวมสุทธิจากตารางราคาที่กำหนดไว้

- `Live Controls`
  ใช้เริ่มและหยุดการตรวจจับผ่านกล้อง

- `Quick Tips`
  คำแนะนำการจัดกล้องและการลดอาการหน่วง

## โครงสร้างไฟล์หลัก

- `app.py`
  Flask server และ endpoint สำหรับ live detection

- `run_app.py`
  launcher หลักสำหรับสร้าง venv, ติดตั้ง dependency และเปิดแอป

- `run_app.sh`
  ตัวเปิดสำหรับ macOS / Linux

- `run_app.bat`
  ตัวเปิดสำหรับ Windows

- `requirements.txt`
  dependency ที่ต้องใช้กับโปรเจกต์

- `services/model_runtime.py`
  ส่วนโหลดโมเดลและรัน inference

- `services/live_detection.py`
  ส่วน decode frame, detect, encode output

- `templates/index.html`
  หน้าเว็บหลัก

- `static/app.js`
  logic ฝั่ง browser

- `static/styles.css`
  layout และสไตล์ของหน้าเว็บ

- `model/`
  โฟลเดอร์เก็บโมเดล

## ปัญหาที่พบบ่อย

### ไม่พบโมเดล

อาการ:
- โปรแกรมแจ้งว่าไม่พบ `kanom_v2.pt`

วิธีแก้:
- วางไฟล์ `kanom_v2.pt` ในโฟลเดอร์ `model/`

### Browser ไม่เปิดอัตโนมัติ

อาการ:
- แอปรันแล้วแต่ browser ไม่เด้งขึ้นเอง

วิธีแก้:
- เปิด URL ที่แสดงใน terminal ด้วยตัวเอง

### กล้องไม่ทำงาน

อาการ:
- กด `Start Detection` แล้วไม่เห็นภาพจากกล้อง

วิธีแก้:
- อนุญาตสิทธิ์กล้องใน browser
- ปิดโปรแกรมอื่นที่ใช้ webcam อยู่
- รีเฟรชหน้าเว็บแล้วลองใหม่

### FPS ต่ำ

สิ่งที่ควรรู้:
- คอขวดหลักมักอยู่ที่การรันโมเดลบน CPU
- แม้เลือก `640` แล้ว FPS ยังอาจต่ำได้ตามสเปกเครื่อง

วิธีปรับปรุง:
1. ลด `Resolution` เป็น `320`
2. ปิดโปรแกรมอื่นที่ใช้ CPU/GPU
3. ใช้เครื่องที่รองรับ `CUDA` หรือ `MPS` ถ้ามี
4. จัดแสงและวางสินค้าให้เห็นชัดในเฟรม

## สถานะไฟล์ติดตั้ง

ตรวจแล้ว:
- `run_app.py` มี syntax ถูกต้อง
- `run_app.sh` มี syntax ถูกต้อง
- `run_app.bat` มีอยู่พร้อมใช้งาน
- `requirements.txt` มีอยู่พร้อมใช้งาน

dependency ปัจจุบันใน `requirements.txt`:
- `Flask`
- `waitress`
- `opencv-python`
- `ultralytics`
- `Pillow`

## หมายเหตุ

- แอปประมวลผลในเครื่อง ไม่ส่งภาพขึ้น cloud
- โปรเจกต์นี้ใช้เฉพาะการตรวจจับผ่านกล้องสด
- ไม่มีโหมดอัปโหลดภาพหรือวิดีโอ
- README นี้อ้างอิงจากสถานะโค้ดปัจจุบันของโปรเจกต์
