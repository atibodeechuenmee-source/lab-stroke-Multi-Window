# Stage 06: Modeling

## Purpose

ฝึกและเปรียบเทียบ model สำหรับ stroke-risk prediction โดยต้องมี single-shot baseline เป็น comparator เสมอ เพื่อวัดประโยชน์ของ temporal features

## Input

- Single-shot baseline feature table จาก Stage 05
- Extract Set 1/2/3 feature tables จาก Stage 05
- Patient-level stroke labels จาก Stage 02

## Process

1. Baseline model:
   - ใช้ single-shot features จาก latest pre-reference record
   - train Logistic Regression with balanced class weight
2. Temporal models:
   - train Logistic Regression บน Extract Set 1/2/3
   - ใช้ `class_weight="balanced"` เป็น default
3. Optional comparator models:
   - Random Forest
   - XGBoost
   - ใช้เพื่อดู nonlinear patterns แต่ไม่แทน Logistic Regression baseline
4. Cross-validation:
   - default ตาม paper คือ LOOCV
   - ถ้า computational cost สูง ให้ใช้ patient-level stratified CV และระบุว่าเป็น deviation จาก paper
5. Threshold handling:
   - เก็บ predicted probability
   - รายงาน metrics ที่ threshold default 0.5
   - ทำ threshold analysis ใน validation stage ถ้าจำเป็น

## Output

- Model predictions ต่อ patient
- Predicted probability
- Predicted class
- Model configuration log
- CV fold assignment หรือ LOOCV prediction table
- Baseline vs temporal model comparison inputs สำหรับ Stage 08

## Checks / Acceptance Criteria

- Train/test split หรือ CV ต้อง split ระดับ patient ไม่ใช่ record
- ไม่มี patient เดียวกันอยู่ทั้ง train และ test ใน fold เดียวกัน
- Baseline model ใช้ single-shot features เท่านั้น
- Temporal model ใช้ Extract Set 1/2/3 ตามนิยาม
- Logistic Regression ใช้ `class_weight="balanced"`
- Predictions ทุก model ต้อง map กลับไปที่ patient id ได้

## Relation to Paper

Paper ใช้ Logistic Regression with `class_weight="balanced"` และ LOOCV เพราะข้อมูล imbalance สูงและต้องการ patient-level independence Stage นี้จึงใช้แนวทางเดียวกันเป็น default

