# Dataset Description

เอกสารนี้อธิบายชุดข้อมูล `patients_with_tc_hdl_ratio_with_drugflag.xlsx` หลังจากทำ EDA เบื้องต้น เพื่อใช้เป็น data dictionary และ reference สำหรับงานวิเคราะห์ต่อไป

## ภาพรวมข้อมูล

- ชื่อไฟล์ข้อมูล: `patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- จำนวนแถว: 218,772 records
- จำนวนคอลัมน์: 30 columns
- ช่วงวันที่ในข้อมูล: 2014-10-01 ถึง 2024-06-30
- หน่วยข้อมูลในแต่ละแถว: 1 record ของการเข้ารับบริการ/การตรวจของผู้ป่วย โดยระบุ `hn` และ `vstdate`

## กลุ่มตัวแปรใน Dataset

ชุดข้อมูลนี้สามารถแบ่งตัวแปรออกเป็นกลุ่มหลัก ๆ ได้ดังนี้:

- ข้อมูลระบุตัวผู้ป่วยและวันที่: `hn`, `vstdate`
- ข้อมูลประชากรและร่างกาย: `sex`, `age`, `height`, `bw`, `bmi`
- พฤติกรรมสุขภาพ: `smoke`, `drinking`
- ความดันโลหิต: `bps`, `bpd`
- ผลแล็บไขมันและเมตาบอลิก: `HDL`, `LDL`, `Triglyceride`, `Cholesterol`, `FBS`, `TC:HDL_ratio`
- การทำงานของไต: `eGFR`, `Creatinine`
- การวินิจฉัยและพื้นที่: `PrincipleDiagnosis`, `ComorbidityDiagnosis`, `ตำบล`
- โรคร่วม/flag ทางคลินิก: `AF`, `heart_disease`, `hypertension`, `diabetes`
- ข้อมูลยา: `ยาที่ได้รับ`, `Statin`, `Gemfibrozil`, `Antihypertensive_flag`

## Data Dictionary

| Column | Type | คำอธิบาย |
|---|---:|---|
| `hn` | int64 | รหัสผู้ป่วย ใช้เชื่อม record ของผู้ป่วยรายเดียวกัน |
| `vstdate` | datetime | วันที่เข้ารับบริการ/วันที่มีข้อมูล record |
| `sex` | int64 | เพศของผู้ป่วย เข้ารหัสเป็นตัวเลข |
| `age` | int64 | อายุผู้ป่วย ณ วันที่ record |
| `height` | float64 | ส่วนสูง |
| `bw` | float64 | น้ำหนักตัว |
| `bmi` | float64 | ดัชนีมวลกาย |
| `smoke` | int64 | สถานะ/ระดับการสูบบุหรี่ เข้ารหัสเป็นตัวเลข |
| `drinking` | int64 | สถานะ/ระดับการดื่มแอลกอฮอล์ เข้ารหัสเป็นตัวเลข |
| `bps` | float64 | ความดันโลหิตตัวบน systolic blood pressure |
| `bpd` | float64 | ความดันโลหิตตัวล่าง diastolic blood pressure |
| `HDL` | float64 | ค่า HDL cholesterol |
| `LDL` | float64 | ค่า LDL cholesterol |
| `Triglyceride` | float64 | ค่า triglyceride |
| `Cholesterol` | float64 | ค่า total cholesterol |
| `AF` | int64 | flag/สถานะ atrial fibrillation หรือข้อมูล AF ตามการเข้ารหัสของ dataset |
| `FBS` | float64 | ค่า fasting blood sugar |
| `eGFR` | float64 | ค่า estimated glomerular filtration rate |
| `Creatinine` | float64 | ค่า creatinine |
| `PrincipleDiagnosis` | string | รหัส/ข้อความการวินิจฉัยหลัก |
| `ComorbidityDiagnosis` | string | รหัส/ข้อความโรคร่วมหรือการวินิจฉัยร่วม |
| `ตำบล` | string | ข้อมูลตำบล/พื้นที่ของผู้ป่วย |
| `ยาที่ได้รับ` | string | รายการยาที่ผู้ป่วยได้รับ |
| `heart_disease` | int64 | flag โรคหัวใจ |
| `hypertension` | int64 | flag โรคความดันโลหิตสูง |
| `diabetes` | int64 | flag โรคเบาหวาน |
| `Statin` | int64 | flag การได้รับยา statin |
| `Gemfibrozil` | int64 | flag การได้รับยา gemfibrozil |
| `TC:HDL_ratio` | float64 | อัตราส่วน total cholesterol ต่อ HDL |
| `Antihypertensive_flag` | int64 | flag การได้รับยาลดความดันโลหิต |

## Missing Values

| Column | Missing | Missing % |
|---|---:|---:|
| `hn` | 0 | 0.00 |
| `vstdate` | 0 | 0.00 |
| `sex` | 0 | 0.00 |
| `age` | 0 | 0.00 |
| `height` | 243 | 0.11 |
| `bw` | 226 | 0.10 |
| `bmi` | 413 | 0.19 |
| `smoke` | 0 | 0.00 |
| `drinking` | 0 | 0.00 |
| `bps` | 27,608 | 12.62 |
| `bpd` | 27,483 | 12.56 |
| `HDL` | 154,022 | 70.40 |
| `LDL` | 155,180 | 70.93 |
| `Triglyceride` | 157,488 | 71.99 |
| `Cholesterol` | 153,319 | 70.08 |
| `AF` | 0 | 0.00 |
| `FBS` | 162,187 | 74.14 |
| `eGFR` | 146,847 | 67.12 |
| `Creatinine` | 141,851 | 64.84 |
| `PrincipleDiagnosis` | 2 | 0.00 |
| `ComorbidityDiagnosis` | 58,758 | 26.86 |
| `ตำบล` | 15,227 | 6.96 |
| `ยาที่ได้รับ` | 40,047 | 18.31 |
| `heart_disease` | 0 | 0.00 |
| `hypertension` | 0 | 0.00 |
| `diabetes` | 0 | 0.00 |
| `Statin` | 0 | 0.00 |
| `Gemfibrozil` | 0 | 0.00 |
| `TC:HDL_ratio` | 155,033 | 70.87 |
| `Antihypertensive_flag` | 0 | 0.00 |

## ค่าสรุปเบื้องต้นของตัวแปรสำคัญ

| Column | Count | Mean | Min | Max |
|---|---:|---:|---:|---:|
| `age` | 218,772 | 62.78 | 18 | 103 |
| `height` | 218,529 | 158.14 | 140.00 | 194.00 |
| `bw` | 218,546 | 62.46 | 30.00 | 132.00 |
| `bmi` | 218,359 | 24.91 | 11.39 | 49.22 |
| `bps` | 191,164 | 134.50 | 60.00 | 218.00 |
| `bpd` | 191,289 | 76.65 | 20.00 | 134.00 |
| `HDL` | 64,750 | 53.83 | 8.00 | 125.00 |
| `LDL` | 63,592 | 113.71 | -30.00 | 369.00 |
| `Triglyceride` | 61,284 | 136.20 | 1.00 | 427.00 |
| `Cholesterol` | 65,453 | 195.23 | 26.00 | 391.00 |
| `FBS` | 56,585 | 109.40 | 50.00 | 296.00 |
| `eGFR` | 71,925 | 75.70 | 1.00 | 188.74 |
| `Creatinine` | 76,921 | 1.01 | 0.08 | 6.59 |
| `TC:HDL_ratio` | 63,739 | 3.85 | 0.60 | 23.75 |

## ข้อสังเกตจาก EDA

- Dataset มีจำนวน record มากและครอบคลุมช่วงเวลาประมาณ 10 ปี
- คอลัมน์พื้นฐาน เช่น `hn`, `vstdate`, `sex`, `age`, flag โรคร่วม และ flag ยา ไม่มี missing values
- ผลแล็บหลายคอลัมน์มี missing values สูงมาก โดยเฉพาะ `FBS`, `Triglyceride`, `LDL`, `TC:HDL_ratio`, `HDL`, `Cholesterol`, `eGFR` และ `Creatinine`
- ค่า `LDL` มีค่าต่ำสุดเป็น -30 ซึ่งควรตรวจสอบเพิ่มเติม เพราะอาจเป็นค่าผิดปกติหรือเกิดจากวิธีคำนวณ/บันทึกข้อมูล
- `TC:HDL_ratio` ขึ้นกับค่าของ cholesterol และ HDL จึงมี missing values สูงตามข้อมูลแล็บที่เกี่ยวข้อง
- ข้อมูล `bps` และ `bpd` มี missing values ประมาณ 12-13% ซึ่งควรพิจารณาวิธีจัดการก่อนนำไปสร้างโมเดล
- คอลัมน์ diagnosis และ medication เป็น string จึงควรวางแผน encoding หรือ feature extraction เพิ่มเติมหากจะใช้ในการสร้างโมเดล

## แนวทางใช้งาน Dataset ต่อ

- ตรวจสอบความหมายของรหัสในคอลัมน์ categorical/flag เช่น `sex`, `smoke`, `drinking`, `AF`
- ตรวจสอบ outliers ของผลแล็บและความดันโลหิต โดยดูไฟล์ `output/boxplot_*.png`
- ตัดสินใจวิธีจัดการ missing values แยกตามชนิดข้อมูล เช่น ลบ record, impute, หรือสร้าง missing indicator
- หากนำไปทำ machine learning ควรกำหนด target variable ให้ชัดเจนก่อน เช่น ทำนายโรค ทำนายการได้รับยา หรือจำแนกกลุ่มความเสี่ยง
- ระวัง data leakage หากใช้คอลัมน์ยา/diagnosis เป็น feature ในงานที่ target เกี่ยวข้องกับโรคหรือการรักษาโดยตรง
