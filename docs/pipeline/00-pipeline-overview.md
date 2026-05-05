# Pipeline Overview

## Goal

วางลำดับงานหลักสำหรับโปรเจกต์ stroke prediction ตั้งแต่ raw data ถึง validation และ deployment optional โดยแยกงานสำรวจข้อมูล งานเตรียมข้อมูล และงานโมเดลให้ชัดเจน

## Inputs

- Raw data: `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Existing EDA script/output: `src/eda.py`, `output/eda_output/`
- Existing feature importance/modeling script/output: `src/feature_importance.py`, `output/feature_importance_output/`
- Patient-level modeling notes/output ถ้าใช้โจทย์ 90-day prediction: `job/patient-level-3month-stroke-prediction.md`, `data/processed/patient_level_90d_stroke.csv`

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
- ทุก output ควรระบุ source data, target definition, และวันที่รัน
