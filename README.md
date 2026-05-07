# Lab Stroke Multi-Window

โปรเจกต์นี้พัฒนา pipeline สำหรับทำนายความเสี่ยง stroke จากข้อมูลเวชระเบียนอิเล็กทรอนิกส์ (EHR) โดยยึดแนวคิดจากงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

เป้าหมายหลักคือเปลี่ยนข้อมูลระดับ visit/record ให้เป็นข้อมูลระดับผู้ป่วย (patient-level) แล้วเปรียบเทียบโมเดลแบบ single-shot baseline กับโมเดลที่ใช้ temporal features จากหลายช่วงเวลาก่อน reference date

## โปรเจกต์นี้ทำอะไร

- อ่านและตรวจสอบ raw EHR data จาก `data/raw`
- ตรวจ schema, missingness, ICD-10 availability และ visit coverage
- สร้าง target สำหรับ stroke จาก ICD-10 codes `I60-I68`
- สร้าง patient-level cohort
- กำหนด `reference date`
  - ผู้ป่วย stroke ใช้ first stroke event date
  - ผู้ป่วย non-stroke ใช้ last visit date
- ตัด records หลัง reference date เพื่อป้องกัน data leakage
- สร้าง temporal windows ตาม paper:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- ตรวจ temporal completeness ว่าผู้ป่วยมีข้อมูลครบสำหรับ feature engineering หรือไม่
- สร้าง feature tables เบื้องต้น:
  - single-shot baseline
  - Extract Set 1
  - Extract Set 2
  - Extract Set 3
- เตรียมโครง modeling/validation ด้วย Logistic Regression, G-Mean และ McNemar's test

## โครงสร้างโปรเจกต์

```text
data/
  raw/                         raw EHR data
docs/
  pipeline/                    เอกสาร pipeline ราย stage
job/                           สรุปงาน implementation ราย stage
output/                        output จากการรัน pipeline/audit
paper/                         paper notes และ PDF reference
src/                           source code ของ pipeline
WORKLOG.md                     บันทึกงานที่ทำ
README.md                      ภาพรวมโปรเจกต์
```

## เอกสาร Pipeline

เอกสารใน `docs/pipeline` แบ่งเป็น 10 stages:

- `00-pipeline-overview.md`: ภาพรวม pipeline ทั้งหมด
- `01-raw-data.md`: raw data audit
- `02-target-and-cohort.md`: target และ patient-level cohort
- `03-data-cleaning.md`: cleaning rules
- `04-eda.md`: exploratory data analysis
- `05-feature-engineering.md`: temporal feature engineering
- `06-modeling.md`: modeling plan
- `07-feature-importance.md`: feature importance, ANOVA, PCA
- `08-validation.md`: validation metrics และ McNemar's test
- `09-deployment-optional.md`: deployment considerations

## โค้ดที่มีแล้ว

- `src/raw_data.py`: Stage 01 raw data audit
- `src/target_cohort.py`: Stage 02 target/cohort construction
- `src/temporal_pipeline.py`: pipeline รวมตั้งแต่ raw audit ถึง feature tables และ optional modeling

## วิธีรัน

รัน Stage 01 raw data audit:

```powershell
python -m src.raw_data
```

รัน Stage 02 target/cohort:

```powershell
python -m src.target_cohort
```

รัน pipeline รวมแบบไม่ train model:

```powershell
python -m src.temporal_pipeline --skip-modeling
```

รัน pipeline รวมพร้อม modeling:

```powershell
python -m src.temporal_pipeline
```

## Output สำคัญ

Stage 01 output:

```text
output/raw_data_output/
```

ตัวอย่างไฟล์:

- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `visit_coverage_summary.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_report.md`

Stage 02 output:

```text
output/target_cohort_output/
```

ตัวอย่างไฟล์:

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `cohort_attrition_report.csv`
- `target_cohort_report.md`

Pipeline รวม output:

```text
output/pipeline_runs/temporal_pipeline/
```

## ผลลัพธ์ล่าสุดจากข้อมูลปัจจุบัน

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

ค่า `temporal-complete patients = 13` เป็นสัญญาณสำคัญว่า completeness criteria แบบ paper เข้มมากกับข้อมูลชุดนี้ ดังนั้น stage ถัดไปควรพิจารณา sensitivity analysis ด้วย window definition อื่น เช่น 90/180 วัน หรือปรับเกณฑ์ completeness ให้เหมาะกับข้อมูลจริง

## Paper Reference

- Note: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- PDF: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- IEEE: https://ieeexplore.ieee.org/abstract/document/11431866

## สถานะปัจจุบัน

Implemented:

- Stage 01 raw data audit
- Stage 02 target/cohort construction
- temporal pipeline โครงรวม
- pipeline documentation ครบ stages 00-09
- paper summary และ job notes

Next:

- Implement Stage 03 data cleaning เป็น module แยก
- Implement Stage 04 EDA
- Implement Stage 05 feature engineering แบบแยก stage
- เพิ่ม ANOVA/PCA ใน Stage 07
- เพิ่ม tests สำหรับ ICD detection, reference date logic และ window assignment

