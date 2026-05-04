# Patient-Level 3-Month Stroke Prediction

เอกสารนี้อธิบาย workflow สำหรับทำนายว่าแต่ละผู้ป่วยจะมี primary stroke diagnosis ภายใน 3 เดือนหรือไม่ โดยใช้สคริปต์ `src/patient_level_prediction.py`

## Target Definition

- ใช้ `PrincipleDiagnosis` เป็น source ของ outcome
- Stroke event คือ ICD-10 ช่วง `I60-I69*`
- Prediction horizon คือ 90 วันหลัง index date
- Target ชื่อ `stroke_3m`

## Cohort Definition

- ใช้ `hn` เป็น patient id
- ใช้ `vstdate` เป็น timeline
- Positive patient: เลือก visit ล่าสุดก่อน stroke event แรก และ stroke ต้องเกิดใน 1-90 วันหลัง index date
- Negative patient: เลือก visit ล่าสุดที่ยังมี follow-up อย่างน้อย 90 วันจากวันสุดท้ายใน dataset
- ไม่ใช้ diagnosis/text columns เป็น feature เพื่อป้องกัน data leakage

## Feature Engineering

สร้าง feature จากข้อมูลก่อนหรือเท่ากับ index date เท่านั้น:

- latest features เช่น `age`, `bmi`, `smoke`, `diabetes`, `hypertension`, medication flags
- temporal features ของ vitals/labs เช่น latest, mean, min, max, std, count, missing rate
- history features เช่น visit count และจำนวนวันที่มีประวัติย้อนหลัง

## Models

เปรียบเทียบ 3 โมเดล:

- Logistic Regression baseline
- RandomForest
- XGBoost

ใช้ Stratified K-Fold CV และ holdout test set แบบ patient-level

## Outputs

ไฟล์หลักอยู่ใน:

```text
output/model_output/
```

ไฟล์ที่สร้าง:

- `patient_level_90d_cv_metrics.csv`
- `patient_level_90d_cv_metrics_summary.csv`
- `patient_level_90d_holdout_metrics.csv`
- `patient_level_90d_feature_importance_comparison.csv`
- `patient_level_90d_feature_importance_comparison.png`
- `patient_level_90d_model_report.txt`
- `patient_level_90d_shap_summary_*.png`
- `patient_level_90d_shap_bar_*.png`
- `patient_level_90d_shap_local_positive_*.png`
- `patient_level_90d_shap_local_negative_*.png`

Processed dataset:

```text
data/processed/patient_level_90d_stroke.csv
```

## ผลลัพธ์ล่าสุด

Processed cohort:

- patient-level rows: 13,031
- positive stroke within 90 days: 406
- negative: 12,625
- prevalence: 3.12%
- excluded positive patients outside 90-day horizon: 604

Holdout metrics:

| Model | ROC-AUC | PR-AUC | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost | 0.8390 | 0.1650 | 0.8450 | 0.1248 | 0.6569 | 0.2097 |
| RandomForest | 0.7979 | 0.1555 | 0.9687 | 0.0000 | 0.0000 | 0.0000 |
| Logistic Regression | 0.7787 | 0.1118 | 0.7437 | 0.0783 | 0.6667 | 0.1401 |

ในรอบนี้ XGBoost เป็นโมเดลที่ดีที่สุดเมื่อเรียงตาม PR-AUC และ ROC-AUC จึงถูกใช้สำหรับ SHAP explainability

## ข้อควรระวัง

- ผู้ป่วย stroke ที่ไม่มี visit ก่อน event หรือ event ไม่ได้เกิดภายใน 90 วันหลัง visit ล่าสุดก่อนหน้า จะถูก exclude จาก positive cohort
- ความหมายของโมเดลคือ prediction จากข้อมูลก่อน index date ไม่ใช่การจำแนก record ปัจจุบัน
- หาก positive class น้อยเกินไป ควรทำ sensitivity analysis กับ horizon 6 เดือนหรือ 1 ปี
- RandomForest ที่ threshold 0.5 ไม่ทำนาย positive class ใน holdout รอบนี้ จึงควรเพิ่ม threshold tuning หรือ calibration ในรอบถัดไป
