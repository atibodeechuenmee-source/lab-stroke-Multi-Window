# Stroke Patient Data Exploration

โปรเจกต์นี้ใช้สำหรับสำรวจข้อมูลผู้ป่วยจากไฟล์ Excel และสร้างกราฟวิเคราะห์ข้อมูลเบื้องต้น เพื่อช่วยดูคุณภาพข้อมูล การกระจายของตัวแปร ความสัมพันธ์ของตัวแปร และค่าผิดปกติ

## โปรเจกต์นี้ทำอะไร

สคริปต์หลักของโปรเจกต์คือ `code/preprocess.py` โดยทำงานดังนี้:

- อ่านข้อมูลจากไฟล์ `patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- แสดงข้อมูลเบื้องต้น เช่น จำนวนแถว/คอลัมน์, ตัวอย่างข้อมูล, ชนิดข้อมูล และค่าสถิติเบื้องต้น
- ตรวจสอบ missing values ของแต่ละคอลัมน์
- สร้างกราฟสำรวจข้อมูล เช่น heatmap, histogram, correlation matrix, boxplot และ pairplot
- บันทึกกราฟทั้งหมดเป็นไฟล์ `.png` ลงในโฟลเดอร์ `output`

## ข้อมูลที่ใช้

ไฟล์ข้อมูลหลัก:

```text
patients_with_tc_hdl_ratio_with_drugflag.xlsx
```

ข้อมูลมีตัวแปรเกี่ยวกับผู้ป่วย เช่น อายุ เพศ ค่าร่างกาย ผลแล็บ โรคร่วม ยาที่ได้รับ และ flag ที่เกี่ยวข้องกับยา/โรคบางกลุ่ม

## ผลลัพธ์ที่ได้

หลังรันสคริปต์ จะได้ไฟล์กราฟในโฟลเดอร์:

```text
output/
```

ตัวอย่างไฟล์ผลลัพธ์:

- `missing_values_heatmap.png`
- `feature_distributions.png`
- `correlation_matrix.png`
- `pairplot.png`
- `boxplot_*.png`

## วิธีรันโปรเจกต์

รันคำสั่งนี้จากโฟลเดอร์หลักของโปรเจกต์:

```powershell
.\.venv\Scripts\python.exe .\code\preprocess.py
```

## โครงสร้างโปรเจกต์

```text
.
├── code/
│   └── preprocess.py
├── job/
│   └── EDA-stroke.md
├── output/
├── paper/
│   ├── README.md
│   └── TEMPLATE.md
├── patients_with_tc_hdl_ratio_with_drugflag.xlsx
├── README.md
└── WORKLOG.md
```

## ไฟล์เอกสาร

- `README.md` - อธิบายว่าโปรเจกต์นี้คืออะไร ทำอะไร ใช้งานอย่างไร และได้ผลลัพธ์อะไร
- `DATASET.md` - อธิบาย dataset, data dictionary, missing values และข้อสังเกตจาก EDA
- `job/EDA-stroke.md` - อธิบายขั้นตอนการทำ EDA และผลลัพธ์จากกราฟที่สร้าง
- `paper/` - เก็บสรุปงานวิจัยที่อ่าน พร้อมลิงก์อ้างอิงและ template สำหรับสรุป paper
- `WORKLOG.md` - บันทึกประวัติการแก้ไขและคำอธิบายงานที่อัปเดตในแต่ละครั้ง

## หมายเหตุ

กราฟถูกบันทึกเป็นไฟล์แทนการแสดงผลบนหน้าจอ เพื่อให้รันสคริปต์ซ้ำได้สะดวก และเก็บผลลัพธ์ไว้ตรวจสอบย้อนหลังได้ในโฟลเดอร์ `output`
