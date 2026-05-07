# Stage 03: Data Cleaning and Preprocessing

## Purpose

ทำความสะอาด pre-reference clinical records ตามแนวทาง Data Preprocessing ของ paper โดยรักษา invariant สำคัญคือไม่มี post-reference data

## Input

- `pre_reference_records_with_windows.csv` จาก Stage 02
- Column mapping จาก raw schema
- Diagnosis fields และ clinical variables ที่ใช้ใน paper

## Process

1. Standardize column names:
   - `hn` -> `patient_id`
   - `vstdate` -> `visit_date`
   - diagnosis columns เป็นชื่อมาตรฐาน
   - lab/clinical columns เป็น lowercase consistent names
2. Standardize date formats
3. Coerce numeric variables:
   - BPS, BPD, HDL, LDL, FBS, BMI, eGFR, creatinine, cholesterol, triglyceride, TC:HDL
4. De-identification:
   - drop direct/quasi identifiers ที่ไม่จำเป็น
   - keep patient id เฉพาะ anonymized key สำหรับ patient-level join
5. Drop exact duplicates
6. Normalize diagnosis fields ด้วย ICD-10 tokens
7. Encode binary variables เป็น `{0,1}`:
   - AF
   - smoking
   - alcohol
   - heart disease
   - hypertension
   - diabetes
   - statin
   - antihypertensive
8. Apply plausible range checks:
   - ค่านอกช่วงตั้งเป็น missing
   - เก็บ cleaning log
9. Recheck no post-reference records

## Output

- `cleaned_pre_reference_records.csv`
- `cleaning_report.json`
- `cleaning_report.md`
- `cleaning_log.csv`
- `missing_summary_after_cleaning.csv`
- `range_summary_after_cleaning.csv`
- `binary_flag_encoding_map.csv`
- `diagnosis_normalization_report.csv`
- `column_standardization_report.csv`
- `deidentification_report.csv`

## Checks / Acceptance Criteria

- Cleaned data must keep `patient_id`, `visit_date`, `reference_date`, `stroke`, `window`
- No post-reference records
- Binary columns contain only `0`, `1`, or missing
- Implausible clinical values must be logged
- Diagnosis normalization must preserve ICD-10 signal for audit
- Cleaning must not create new target leakage

## Relation to Paper

Stage นี้ตรงกับ Data Preprocessing ของ paper: remove personally identifiable information, harmonize dates/units/names, handle implausible/duplicated entries, encode binary clinical attributes และ normalize diagnosis fields using ICD-10
