# Modeling

## Goal

สร้างและเปรียบเทียบโมเดลทำนาย stroke ด้วย pipeline ที่ควบคุม leakage, class imbalance และ reproducibility

โมเดลหลักต้องทำนาย `stroke_3m` ระดับคนไข้ ไม่ใช่ `stroke_flag` ระดับ visit/record

## Inputs

- Feature table
- Target column: `stroke_3m`
- Patient-level train/test split

## Steps

1. แบ่ง train/test ระดับคนไข้โดยใช้ stratification ตาม `stroke_3m`
2. สร้าง preprocessing pipeline เช่น imputation, missing indicator, scaling หรือ encoding ตามชนิดโมเดล
3. สร้าง baseline model เช่น Logistic Regression
4. Train โมเดล tree-based เช่น RandomForest และ XGBoost
5. ใช้ Stratified K-Fold CV บน train set
6. จัดการ class imbalance เช่น class weight, scale_pos_weight หรือ threshold tuning
7. ประเมิน holdout test set หลังเลือก workflow จาก train/CV แล้ว

## Outputs

- Model pipeline objects หรือ scripts
- CV metrics
- Holdout metrics
- Confusion matrix และ classification report
- Model comparison table

## Checks

- Preprocessing ต้องอยู่ใน pipeline เพื่อ fit เฉพาะ train fold
- Test set ใช้ครั้งสุดท้ายสำหรับประเมินเท่านั้น
- ห้ามให้ `hn` เดียวกันอยู่ทั้ง train และ test
- รายงาน ROC-AUC และ PR-AUC เพราะ positive class มีน้อย
- ตรวจ precision, recall และ threshold ไม่ใช้ accuracy อย่างเดียว
