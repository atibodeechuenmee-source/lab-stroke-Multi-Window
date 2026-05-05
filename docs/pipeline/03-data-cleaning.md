# Data Cleaning

## Goal

ทำให้ข้อมูลมีรูปแบบพร้อมใช้งานและลด error จาก missing, type mismatch, duplicate, invalid values และ outliers โดยยังรักษาสัญญาณทางคลินิกที่สำคัญไว้

## Inputs

- Raw data พร้อม target/cohort definition
- Schema summary และ missing summary จากขั้นตอน raw data/EDA

## Steps

1. แปลงชนิดข้อมูลให้ถูกต้อง เช่น date, numeric labs/vitals, binary flags
2. ตรวจ duplicate rows และ duplicate patient-visit records
3. จัดการ missing values แยกตามชนิดข้อมูล เช่น demographic, vitals, labs, medication flags
4. กำหนด rule สำหรับ impossible values เช่น อายุหรือน้ำหนักที่ผิดธรรมชาติ
5. ตรวจ outliers ของ lab/vital values และตัดสินใจว่าจะ keep, cap, set missing, หรือ exclude
6. บันทึก cleaning log ว่ามี rows/values ถูกแก้หรือ exclude เท่าไร

## Outputs

- Cleaned dataset หรือ cleaning-ready dataframe
- Cleaning rules document
- Cleaning log summary
- Missing/outlier summary หลัง cleaning

## Checks

- Imputer, scaler, encoder หรือ threshold ที่เรียนรู้จาก distribution ต้อง fit จาก train set เท่านั้น
- Outlier rule ต้องไม่ใช้ target ในการตัดสินใจโดยตรง
- ไม่ลบ positive class มากเกินไปโดยไม่รายงานผลกระทบ
- เก็บ missing indicator เมื่อ missing pattern อาจมีความหมายทางคลินิก
