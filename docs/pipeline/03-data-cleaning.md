# Stage 03: Data Cleaning

## Purpose

ทำความสะอาดข้อมูล clinical records ที่ผ่าน cohort rules แล้ว เพื่อให้พร้อมสำหรับ EDA และ feature engineering โดยรักษาหลักการไม่ใช้ post-reference data

## Input

- Pre-reference records จาก Stage 02
- Patient-level cohort table
- Raw schema summary จาก Stage 01
- Column mapping และ expected units

## Process

1. De-identification:
   - เก็บเฉพาะ anonymized patient id หรือ `HN` ที่จำเป็น
   - ไม่ส่งออก personally identifiable information
2. Standardization:
   - แปลง date format ให้เป็นมาตรฐานเดียว
   - standardize column names
   - standardize measurement units
3. Duplicate handling:
   - ตรวจ duplicate records ตาม patient id, visit date, diagnosis และ lab values
   - กำหนด rule ว่าจะ drop exact duplicates เท่านั้น
4. Implausible value handling:
   - ตรวจค่าที่เป็นไปไม่ได้ เช่น blood pressure ติดลบ, HDL เป็นศูนย์, creatinine ติดลบ
   - แทนค่าผิดปกติด้วย missing value และบันทึกลง cleaning log
5. Binary flag encoding:
   - smoking, drinking, AF, diabetes, hypertension, heart disease
   - statin flag และ antihypertensive flag
   - ใช้ encoding `{0, 1}` เป็น default
6. Diagnosis normalization:
   - normalize ICD-10 codes
   - เก็บ principal และ comorbidity diagnosis ในรูปแบบที่ตรวจซ้ำได้

## Output

- Cleaned pre-reference records
- Cleaning report
- Missing summary after cleaning
- Range summary after cleaning
- Binary flag encoding map
- Diagnosis normalization report

## Checks / Acceptance Criteria

- ไม่มี personally identifiable information ที่ไม่จำเป็นใน output
- Date columns เป็น type ที่ใช้คำนวณ window ได้
- Binary flags มีค่าเฉพาะ `0`, `1` หรือ missing ก่อน imputation/aggregation
- ไม่มี implausible values ที่ควรถูก flag ค้างอยู่โดยไม่บันทึกเหตุผล
- ยืนยันอีกครั้งว่า output ยังไม่มี post-reference records

## Relation to Paper

Paper ระบุ preprocessing เช่น de-identification, harmonized dates/units/variables, implausible value handling, binary encoding และ ICD-10 normalization ก่อนสร้าง temporal features

