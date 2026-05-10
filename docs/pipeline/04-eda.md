# Stage 04: Exploratory Data Analysis

## Purpose

ตรวจข้อมูลหลัง cleaning เพื่อประเมินว่าสามารถทำตาม paper ได้มากแค่ไหน โดยเฉพาะ class imbalance, temporal coverage, missingness และผลกระทบของ completeness criteria

## Input

- `cleaned_pre_reference_records.csv` จาก Stage 03
- `patient_level_cohort.csv` จาก Stage 02
- `temporal_completeness_flags.csv` จาก Stage 02
- `cohort_attrition_report.csv` จาก Stage 02

## Process

1. Class imbalance:
   - จำนวน stroke patients
   - จำนวน non-stroke patients
   - stroke prevalence
2. Visit frequency:
   - visits per patient
   - follow-up duration
   - time gaps between visits
3. Temporal coverage:
   - patients with FIRST visit
   - patients with MID visit
   - patients with LAST visit
   - patients complete in all windows
   - records that contribute to multiple overlapping windows
4. Missingness:
   - by variable
   - by stroke label
   - by window
5. Clinical descriptive statistics:
   - all patients
   - stroke vs non-stroke
6. Leakage audit:
   - confirm `visit_date <= reference_date`
7. Attrition interpretation:
   - compare raw cohort vs temporal-complete cohort

## Output

- `class_imbalance.csv`
- `visit_frequency_by_patient.csv`
- `visit_frequency_distribution.csv`
- `window_visit_counts.csv`
- `time_gap_summary.csv`
- `missingness_by_variable.csv`
- `missingness_by_stroke.csv`
- `missingness_by_window.csv`
- `temporal_coverage_summary.csv`
- `clinical_descriptive_stats.csv`
- `high_missing_variables.csv`
- `leakage_audit_summary.csv`
- `eda_summary_report.json`
- `eda_summary_report.md`

## Checks / Acceptance Criteria

- Must report class imbalance
- Must report temporal-complete patient count
- Must show missingness by FIRST/MID/LAST
- Must report overlapping window membership behavior
- Must confirm no post-reference records
- Must identify whether strict paper completeness leaves enough stroke cases
- Must recommend sensitivity analysis if temporal-complete cohort is too small

## Relation to Paper

Paper emphasizes that real-world EHR are irregular, incomplete and heterogeneous. Stage นี้ตรวจว่าข้อมูลของเรามีปัญหานี้มากแค่ไหน และความเข้มของ completeness criteria แบบ paper ทำให้ sample size ลดลงเท่าไร
