# EDA

## Goal

สำรวจข้อมูลเพื่อเข้าใจ distribution, missing pattern, class imbalance, correlation และ outliers ก่อนสร้าง features และโมเดล

สำหรับโจทย์นี้ EDA ต้องแยกให้ชัดว่า `stroke_flag` เป็น event marker ระดับ record ส่วน target หลักของโมเดลคือ `stroke_3m` ระดับคนไข้

## Inputs

- Raw หรือ cleaned dataset ตามวัตถุประสงค์ของ EDA
- Existing EDA script: `src/eda.py`
- Existing outputs: `output/eda_output/`

## Steps

1. สรุป schema, dtype, missing count, missing percent
2. ตรวจ distribution ของ numeric features เช่น age, BMI, blood pressure, labs
3. ตรวจ categorical/flag features เช่น sex, smoke, drinking, comorbidity flags, medication flags
4. ตรวจ `stroke_3m` distribution และ class imbalance ระดับคนไข้
5. ตรวจ correlation ระหว่าง numeric features
6. ตรวจ outliers ผ่าน boxplot และ percentile summary
7. สรุปข้อค้นพบที่ส่งผลต่อ cleaning, feature engineering และ modeling

## Outputs

- `column_types.csv`
- `missing_summary.csv`
- `numeric_summary.csv`
- missing value plots
- distribution plots
- correlation plots
- outlier plots
- EDA findings summary
- patient-level target distribution ของ `stroke_3m`

## Checks

- EDA เพื่อรายงานภาพรวมทำบนข้อมูลทั้งหมดได้ แต่ insight ที่กำหนด preprocessing rule สำหรับโมเดลต้องตรวจซ้ำบน train set
- ระวัง correlation ที่เกิดจาก derived features เช่น `TC:HDL_ratio`
- ระบุ features ที่มี missing สูงและควรมี missing indicator
- ระบุ features ที่เสี่ยง leakage เช่น diagnosis/text columns
- ห้ามตีความ `stroke_flag` ระดับ record เป็น target หลักของ future prediction
