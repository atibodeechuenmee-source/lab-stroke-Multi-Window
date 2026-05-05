# Pipeline Overview

## Goal

วางลำดับงานหลักสำหรับโปรเจกต์ stroke prediction ตั้งแต่ raw data ถึง validation และ deployment optional โดยแยกงานสำรวจข้อมูล งานเตรียมข้อมูล และงานโมเดลให้ชัดเจน

โจทย์หลักของโปรเจกต์นี้คือทำนายระดับคนไข้ว่า **คนไข้จะเกิด primary stroke diagnosis ภายใน 90 วันหลัง index date หรือไม่** ดังนั้น target หลักสำหรับ modeling คือ `stroke_3m` ไม่ใช่ `stroke_flag` ระดับแถว

## Inputs

- Raw data: `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Existing EDA script/output: `src/eda.py`, `output/eda_output/`
- Patient-level modeling script/output: `src/patient_level_prediction.py`, `data/processed/patient_level_90d_stroke.csv`, `output/model_output/`
- `stroke_flag` ใช้เป็น event marker จาก `PrincipleDiagnosis` เพื่อหา stroke event date เท่านั้น

## Steps

1. Raw Data
2. Target & Cohort Definition
3. Data Cleaning
4. EDA
5. Feature Engineering
6. Modeling
7. Feature Importance
8. Validation
9. Deployment optional

## Outputs

- เอกสารและ artifact ของแต่ละขั้นตอน
- Cleaned/intermediate data ที่ตรวจสอบย้อนกลับได้
- Feature table สำหรับ modeling
- Model metrics, feature importance, SHAP, validation report

## Checks

- แยก raw data ออกจาก processed data เสมอ
- ทุก rule ที่เรียนรู้จากข้อมูล เช่น imputation, scaling, encoding, threshold ควร fit จาก train set เท่านั้น
- หลีกเลี่ยงการใช้ diagnosis/text field ที่ทำให้เกิด target leakage
- Train/test split และ validation ต้องทำระดับคนไข้ ไม่ให้ `hn` เดียวกันอยู่ทั้ง train และ test
- ทุก output ควรระบุ source data, target definition, และวันที่รัน
