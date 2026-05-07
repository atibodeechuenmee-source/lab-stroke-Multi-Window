# Stage 02: Target and Cohort Construction

## Purpose

สร้าง patient-level cohort และ target label ตาม paper โดยใช้ ICD-10 `I60-I68` เพื่อระบุ stroke และกำหนด `reference date` ให้ถูกต้องก่อนสร้าง features

Stage นี้เป็นจุดกัน data leakage ที่สำคัญที่สุด เพราะทุก stage หลังจากนี้ต้องใช้เฉพาะ records ก่อนหรือเท่ากับ `reference date`

## Input

- Raw EHR data จาก Stage 01
- Required columns:
  - patient id
  - visit date
  - principal diagnosis
  - comorbidity diagnosis
  - core clinical variables

## Process

1. Normalize visit date เป็น datetime
2. Identify stroke events ด้วย ICD-10 `I60-I68`
3. Build patient-level cohort:
   - first visit date
   - last visit date
   - first stroke date
   - record count
   - stroke label
4. Define `reference date`:
   - stroke patient = first stroke event date
   - non-stroke patient = last clinical visit date
5. Remove all records after `reference date`
6. Calculate months before reference:

```text
months_before_reference = (reference_date - visit_date) / 30.4375
```

7. Assign temporal windows:
   - FIRST: 21-9 months
   - MID: 18-6 months
   - LAST: 15-3 months
8. Build temporal completeness flags:
   - has visit in every window
   - has core clinical variables in every window
9. Build cohort attrition report

## Output

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `cohort_attrition_report.csv`
- `target_cohort_summary.json`
- `target_cohort_report.md`

## Checks / Acceptance Criteria

- Stroke patients must use first stroke event as `reference date`
- Non-stroke patients must use last clinical visit as `reference date`
- No record after `reference date`
- Window assignment must use paper-default FIRST/MID/LAST
- Attrition report must show how many patients remain after temporal completeness
- Temporal-complete cohort must be reported separately from all pre-reference patients

## Relation to Paper

Stage นี้ตรงกับ Data Selection ของ paper ซึ่งกำหนด ICD-10 `I60-I68`, reference date, post-event leakage removal, temporal windows และ completeness criteria ก่อนสร้าง temporal representations
