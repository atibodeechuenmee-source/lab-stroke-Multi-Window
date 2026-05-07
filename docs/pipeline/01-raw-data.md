# Stage 01: Raw Data Audit

## Purpose

ตรวจ raw EHR data ก่อนทำ cohort/feature engineering ให้ตรงกับข้อมูลที่ paper ใช้ โดยไม่แก้ไขไฟล์ raw ต้นทาง

Paper ใช้ EHR จาก Chokchai Hospital จำนวน 245,978 records จากผู้ป่วย 19,473 คน และเลือก clinical variables ที่เกี่ยวข้องกับ stroke risk จาก attributes เดิม 45 ตัว โปรเจกต์ของเราต้อง audit raw data ให้รู้ว่ามีคอลัมน์สำคัญครบหรือไม่ก่อนทำ stage ถัดไป

## Input

- Raw EHR file เช่น `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Expected columns:
  - patient id / HN
  - visit date
  - principal diagnosis
  - comorbidity diagnosis
  - age, sex
  - BPS, BPD
  - HDL, LDL, total cholesterol, triglycerides
  - FBS, BMI, eGFR, creatinine
  - AF, smoking, alcohol
  - medication / dispensed drugs
  - diabetes, hypertension, heart disease
  - statin, antihypertensive
  - TC:HDL ratio ถ้ามี

## Process

1. Read raw Excel/CSV แบบ read-only
2. สร้าง schema summary:
   - column name
   - dtype
   - missing count / missing percent
   - unique count
   - example values
3. ตรวจ availability ของ columns ที่ paper ใช้
4. ตรวจ diagnosis columns ว่ามี ICD-10 `I60-I68` หรือไม่
5. ตรวจ visit coverage ต่อ patient:
   - จำนวน visits
   - first visit
   - last visit
   - follow-up duration
6. ตรวจ plausible ranges เบื้องต้นโดยไม่แก้ข้อมูล
7. เขียน raw audit report

## Output

- `raw_column_list.csv`
- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `raw_range_summary.csv`
- `visit_coverage_summary.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_report.json`
- `raw_data_report.md`

## Checks / Acceptance Criteria

- ไฟล์ raw ต้องไม่ถูกแก้ไข
- ต้องพบ patient id และ visit date
- ต้องพบ diagnosis column อย่างน้อยหนึ่งคอลัมน์
- ต้องตรวจ ICD-10 `I60-I68`
- ต้องรายงาน missingness ของตัวแปรหลักที่ paper ใช้
- ต้องรายงาน visit coverage เพราะ temporal windows ต้องพึ่ง longitudinal records

## Relation to Paper

Stage นี้สอดคล้องกับส่วน Data Collection ของ paper โดยตรวจว่าข้อมูลของเรามีโครงใกล้กับ EHR ที่ paper ใช้หรือไม่ และพร้อมสำหรับการคัด cohort ตาม ICD-10, reference date และ temporal completeness หรือไม่
