# Lab Stroke Multi-Window

โปรเจกต์นี้พัฒนา pipeline สำหรับทำนายความเสี่ยง stroke จากข้อมูลเวชระเบียนอิเล็กทรอนิกส์ (EHR) โดยยึดแนวคิดจากงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

แกนหลักของงานคือแปลงข้อมูลระดับ visit/record ให้เป็นข้อมูลระดับผู้ป่วย (patient-level) แล้วเปรียบเทียบ `single-shot baseline` กับโมเดลที่ใช้ temporal features จากหลายช่วงเวลาก่อน `reference date`

## โปรเจกต์นี้ทำอะไร

- ตรวจสอบ raw EHR data จาก `data/raw`
- ตรวจ schema, missingness, ICD-10 availability และ visit coverage
- สร้าง target stroke จาก ICD-10 codes `I60-I68`
- สร้าง patient-level cohort
- กำหนด `reference date`
- ลบ records หลัง `reference date` เพื่อป้องกัน data leakage
- สร้าง temporal windows ตาม paper:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- สร้าง feature tables:
  - `single-shot baseline`
  - `Extract Set 1`
  - `Extract Set 2`
  - `Extract Set 3`
- ทำ modeling ด้วย Logistic Regression แบบ `class_weight="balanced"`
- ทำ feature importance ด้วย ANOVA, PCA และ ANOVA+PCA
- ทำ validation ด้วย sensitivity, specificity, G-Mean, ROC-AUC/PR-AUC และ McNemar's test เมื่อข้อมูลพร้อม

## โครงสร้างโปรเจกต์

```text
data/raw/             raw EHR data
docs/pipeline/        เอกสาร pipeline ราย stage
job/                  สรุปงาน implementation ราย stage
output/               output จากการรัน pipeline (ไม่ควร push)
paper/                paper notes และ PDF reference
src/                  source code ของ pipeline
tests/                tests ถ้ามีหรือเพิ่มในอนาคต
README.md             ภาพรวมโปรเจกต์
WORKLOG.md            บันทึกงาน
agent.md              คู่มือสำหรับ AI agent ในโปรเจกต์นี้
```

## Pipeline Stages

- `src/raw_data.py`: Stage 01 raw data audit
- `src/target_cohort.py`: Stage 02 target/cohort construction
- `src/data_cleaning.py`: Stage 03 data cleaning
- `src/eda.py`: Stage 04 exploratory data analysis
- `src/feature_engineering.py`: Stage 05 temporal feature engineering
- `src/modeling.py`: Stage 06 modeling
- `src/feature_importance.py`: Stage 07 feature importance / ANOVA / PCA
- `src/validation.py`: Stage 08 validation
- `src/temporal_pipeline.py`: orchestrator ที่เรียกใช้ Stage 01-08 จาก modules แยก

## วิธีรัน

รันแต่ละ stage แยก:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data
.\.venv\Scripts\python.exe -m src.target_cohort
.\.venv\Scripts\python.exe -m src.data_cleaning
.\.venv\Scripts\python.exe -m src.eda
.\.venv\Scripts\python.exe -m src.feature_engineering
.\.venv\Scripts\python.exe -m src.modeling
.\.venv\Scripts\python.exe -m src.feature_importance
.\.venv\Scripts\python.exe -m src.validation
```

รัน orchestrator รวมถึง Stage 05:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling
```

รัน orchestrator รวมถึง Stage 08:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline
```

ระบุ output directory เอง:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling --output-dir output/pipeline_runs/orchestrator_test
```

## Output สำคัญ

Stage แยกจะเขียน output ที่:

```text
output/raw_data_output/
output/target_cohort_output/
output/data_cleaning_output/
output/eda_output/
output/feature_engineering_output/
output/model_output/
output/feature_importance_output/
output/validation_output/
```

Orchestrator จะเขียน output ที่:

```text
output/pipeline_runs/temporal_pipeline/
```

หรือ path ที่กำหนดผ่าน `--output-dir`

## ผลรันล่าสุดที่ควรรู้

จาก raw file `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`:

- raw rows: 218,772
- columns: 30
- patients: 13,635
- required fields available: 29
- required fields missing: 0
- stroke ICD `I60-I68` record hits: 3,950

จาก Stage 02 target/cohort:

- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13
- no post-reference records: true

จาก Stage 06-08:

- single-shot baseline train/evaluate ได้
- temporal feature sets ถูก skip ใน modeling/feature importance เพราะ temporal-complete cohort มี minority class น้อยเกินไป
- McNemar's test ถูก skip เพราะยังไม่มี temporal predictions ที่ train สำเร็จให้เทียบกับ baseline

## ข้อควรระวัง

- อย่าใช้ข้อมูลหลัง `reference date`
- อย่า commit/push `output/`, `.venv/`, `__pycache__/` หรือ generated patient-level data
- Feature selection/PCA ต้อง fit เฉพาะ training fold
- `G-Mean` เป็น metric หลัก เพราะข้อมูล stroke imbalance สูง
- Strict paper-style temporal completeness ทำให้เหลือ temporal-complete patients เพียง 13 รายในข้อมูลปัจจุบัน จึงควรทำ sensitivity analysis ในอนาคต เช่น window 90/180 วัน

## Paper Reference

- Note: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- PDF: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- IEEE: https://ieeexplore.ieee.org/abstract/document/11431866
