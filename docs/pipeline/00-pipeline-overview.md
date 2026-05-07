# Pipeline Overview: Multi-Window Temporal Stroke-Risk Prediction

## Purpose

เอกสารนี้เป็นภาพรวม pipeline สำหรับสร้าง patient-level stroke-risk prediction ตามแนวทางงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

เป้าหมายหลักคือเปลี่ยน raw EHR records ให้เป็นข้อมูลระดับผู้ป่วยที่ใช้เปรียบเทียบ `single-shot baseline` กับ temporal feature models ได้อย่างชัดเจน โดยต้องป้องกัน data leakage จากข้อมูลหลัง stroke event หรือหลัง `reference date`

## Input

- Raw EHR data จาก `data/raw`
- Paper note หลัก: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- ICD-10 stroke definition: `I60-I68`
- Core clinical variables เช่น blood pressure, lipid labs, glucose, renal markers, diagnosis, medication และ demographic fields

## Process

Pipeline แบ่งเป็น 10 stages:

1. Raw data audit และ data dictionary
2. Target and cohort construction
3. Data cleaning
4. Exploratory data analysis
5. Feature engineering
6. Modeling
7. Feature importance and dimensionality reduction
8. Validation
9. Optional deployment planning

หลักการสำคัญ:

- สร้างหนึ่งแถวต่อหนึ่ง patient ใน final modeling table
- กำหนด `reference date` ให้ชัดเจนก่อนสร้าง feature
- Stroke patient ใช้ first stroke event เป็น `reference date`
- Non-stroke patient ใช้ last clinical visit เป็น `reference date`
- ลบ records หลัง `reference date` ออกทั้งหมด
- ใช้ temporal windows ตาม paper เป็นค่า default:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- สร้าง single-shot baseline จาก latest pre-reference record เพื่อเปรียบเทียบกับ temporal features

## Output

- Stage-level markdown documents ใน `docs/pipeline`
- นิยาม input/output ของแต่ละ stage
- Acceptance criteria สำหรับตรวจคุณภาพก่อนส่งต่อ stage ถัดไป
- Code modules ใน `src`
- Job notes ใน `job`
- Generated artifacts ใน `output`

## Checks / Acceptance Criteria

- มีเอกสารครบ `00` ถึง `09`
- ทุก stage ระบุ `Purpose`, `Input`, `Process`, `Output`, `Checks / Acceptance Criteria`, `Relation to Paper`
- ทุก stage ที่เกี่ยวกับ feature หรือ target ต้องระบุชัดว่าไม่ใช้ post-reference records
- Modeling และ validation ต้องมี single-shot baseline เป็น comparator
- Validation ต้องมี sensitivity, specificity, G-Mean และ McNemar's test เมื่อ paired predictions พร้อม

## Implementation Status

โค้ดปัจจุบันแยก implementation ตาม stage ใน `src/` และมี `src/temporal_pipeline.py` เป็น orchestrator สำหรับเรียกใช้ stage เหล่านั้นแบบ end-to-end

Stage modules:

- Stage 01: `src/raw_data.py`
- Stage 02: `src/target_cohort.py`
- Stage 03: `src/data_cleaning.py`
- Stage 04: `src/eda.py`
- Stage 05: `src/feature_engineering.py`
- Stage 06: `src/modeling.py`
- Stage 07: `src/feature_importance.py`
- Stage 08: `src/validation.py`

Orchestrator:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling
```

ผลทดสอบล่าสุดของ orchestrator แบบ `--skip-modeling` ผ่าน Stage 01-05 สำเร็จ:

- raw rows: 218,772
- patients: 13,635
- stroke patients: 969
- pre-reference records: 194,231
- temporal-complete patients: 13
- Extract Set 1/2/3 ถูกสร้างสำเร็จ

ข้อจำกัดปัจจุบันคือ strict temporal completeness เหลือผู้ป่วยครบทุก window เพียง 13 ราย ทำให้ temporal models ใน Stage 06-08 ยังถูก skip เมื่อ class distribution ไม่พอ

## Relation to Paper

Pipeline นี้ยึด paper เป็น blueprint โดยเฉพาะส่วน patient-level cohort, temporal windows, completeness criteria, Extract Set 1/2/3, Logistic Regression with balanced class weight, G-Mean และ McNemar's test
