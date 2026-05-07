# Stage 00: Pipeline Overview

## Purpose

กำหนดภาพรวม pipeline ของโปรเจกต์ให้ทำตามงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` ให้มากที่สุด โดยใช้ real-world EHR เพื่อสร้าง patient-level stroke-risk prediction และเปรียบเทียบ `single-shot baseline` กับ temporal feature models

เป้าหมายสำคัญคือทำให้ทุก stage ในโปรเจกต์รักษาหลักเดียวกับ paper:

- patient-level cohort
- ICD-10 stroke definition `I60-I68`
- reference date ที่ชัดเจน
- ไม่ใช้ post-reference records
- FIRST/MID/LAST retrospective windows
- Extract Set 1/2/3
- Logistic Regression with `class_weight="balanced"`
- LOOCV หรือ patient-level CV
- sensitivity, specificity, G-Mean
- McNemar's test เมื่อมี paired predictions

## Input

- Raw EHR data ใน `data/raw`
- Paper PDF: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- Paper note: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- Full Thai translation: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.th.md`

## Process

Pipeline แบ่งเป็น stage ตาม paper:

1. Raw data audit
2. Target and cohort construction
3. Data cleaning and preprocessing
4. Exploratory data analysis
5. Temporal feature engineering
6. Modeling
7. Feature importance and dimensionality reduction
8. Validation
9. Optional deployment planning

Paper-default temporal windows:

```text
FIRST = 21-9 เดือนก่อน reference date
MID   = 18-6 เดือนก่อน reference date
LAST  = 15-3 เดือนก่อน reference date
```

Paper-default cohort rules:

- Stroke patient: `reference date` = first stroke event
- Non-stroke patient: `reference date` = last clinical visit
- Remove all records after `reference date`
- Require at least one visit in FIRST/MID/LAST
- Require core clinical variables available in every window

## Output

- Stage documents ใน `docs/pipeline`
- Stage implementations ใน `src`
- Stage job notes ใน `job`
- Generated artifacts ใน `output`
- End-to-end manifest จาก `src.temporal_pipeline`

## Checks / Acceptance Criteria

- ทุก stage ต้องระบุ input/output ชัดเจน
- ไม่มี stage ใดใช้ post-reference data เพื่อสร้าง target, features, model หรือ validation
- Single-shot baseline ต้องถูกเก็บเป็น comparator เสมอ
- Temporal features ต้องอ้างอิง FIRST/MID/LAST ตาม paper เป็น default
- Metrics หลักต้องมี sensitivity, specificity และ G-Mean
- Validation ต้องรองรับ McNemar's test เมื่อมี paired predictions

## Relation to Paper

ไฟล์นี้กำหนดให้ทั้งโปรเจกต์ใช้ paper เป็น blueprint หลัก ไม่ใช่แค่ related work โดย stage 01-08 ต้องออกแบบให้สอดคล้องกับ Data Collection, Data Selection, Preprocessing, Feature Extraction, Feature Selection, PCA, Logistic Regression, LOOCV และ Validation ของ paper
