# งาน: Update Stage 04 Exploratory Data Analysis

## เป้าหมาย

อัปเดต `src/eda.py` ให้ทำ Stage 04 ตาม `docs/pipeline/04-eda.md` ล่าสุด และช่วยประเมินอย่างเป็นระบบว่าข้อมูลปัจจุบันพร้อมทำ temporal stroke-risk prediction ตามงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` แค่ไหน

Stage นี้ไม่สร้าง feature หรือ model แต่ทำหน้าที่ตรวจความพร้อมของข้อมูลหลัง cleaning โดยเน้น class imbalance, missingness, visit coverage, temporal coverage, leakage audit และผลกระทบของ strict FIRST/MID/LAST completeness criteria

หมายเหตุจากภาพ paper: FIRST/MID/LAST เป็น overlapping windows ดังนั้น EDA ควรตรวจจำนวน records/patients ที่ contribute ได้หลาย windows ด้วย ไม่ใช่ดูเพียง exclusive window label

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/eda.py`
- `docs/pipeline/04-eda.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- method context: exploratory review before feature extraction
- EDA principle: quantify irregular, incomplete, heterogeneous EHR before temporal modeling
- default windows: `FIRST`, `MID`, `LAST`

เพิ่ม output/report ใหม่:

- `window_coverage_by_label.csv`
- `temporal_complete_case_summary.csv`
- `sensitivity_analysis_recommendation.csv`
- `eda_acceptance_checks.csv`

เพิ่มการวิเคราะห์ temporal-complete cohort:

- จำนวน temporal-complete patients
- จำนวน temporal-complete stroke patients
- จำนวน temporal-complete non-stroke patients
- stroke prevalence ใน temporal-complete cohort

เพิ่ม sensitivity recommendation:

- ถ้า strict FIRST/MID/LAST temporal-complete cohort มี stroke cases น้อยเกินไป จะ recommend sensitivity analysis
- ค่า threshold ขั้นต่ำตอนนี้คือ temporal-complete stroke cases อย่างน้อย 2 คน เพื่อให้การทำ patient-level CV ขั้นต่ำไม่พัง
- recommendation ยังย้ำว่า paper windows ต้องเป็น primary baseline เสมอ

เพิ่ม summary fields ใน `eda_summary_report.json`:

- `paper_reference`
- `temporal_complete_stroke_patients`
- `temporal_complete_nonstroke_patients`
- `sensitivity_analysis_recommended`
- `acceptance_checks_passed`
- `acceptance_checks_total`
- `acceptance_passed`

## Output จาก Stage 04

Default output directory:

```text
output/eda_output
```

ไฟล์ที่ Stage 04 สร้าง:

- `class_imbalance.csv`
- `visit_frequency_by_patient.csv`
- `visit_frequency_distribution.csv`
- `window_visit_counts.csv`
- `window_coverage_by_label.csv`
- `time_gap_summary.csv`
- `missingness_by_variable.csv`
- `missingness_by_stroke.csv`
- `missingness_by_window.csv`
- `temporal_coverage_summary.csv`
- `temporal_complete_case_summary.csv`
- `sensitivity_analysis_recommendation.csv`
- `clinical_descriptive_stats.csv`
- `high_missing_variables.csv`
- `leakage_audit_summary.csv`
- `eda_acceptance_checks.csv`
- `eda_summary_report.json`
- `eda_summary_report.md`

## Acceptance Checks

`eda_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- รายงาน class imbalance ระดับ patient
- รายงาน temporal-complete patient count
- รายงาน missingness by `FIRST/MID/LAST`
- ยืนยันว่าไม่มี post-reference records
- ระบุจำนวน stroke cases ใน strict temporal-complete cohort
- recommend sensitivity analysis ถ้า temporal-complete stroke cases น้อยเกินไป

## วิธีรัน

ใช้ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.eda
```

ระบุ input/output เอง:

```powershell
.\.venv\Scripts\python.exe -m src.eda --records-path output\pipeline_runs\stage03_update_test\cleaned_pre_reference_records.csv --cohort-path output\pipeline_runs\stage02_update_test\patient_level_cohort.csv --completeness-path output\pipeline_runs\stage02_update_test\temporal_completeness_flags.csv --attrition-path output\pipeline_runs\stage02_update_test\cohort_attrition_report.csv --output-dir output\pipeline_runs\stage04_update_test
```

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\eda.py
```

ผลลัพธ์: ผ่าน

รัน Stage 04:

```powershell
.\.venv\Scripts\python.exe -m src.eda --records-path output\pipeline_runs\stage03_update_test\cleaned_pre_reference_records.csv --cohort-path output\pipeline_runs\stage02_update_test\patient_level_cohort.csv --completeness-path output\pipeline_runs\stage02_update_test\temporal_completeness_flags.csv --attrition-path output\pipeline_runs\stage02_update_test\cohort_attrition_report.csv --output-dir output\pipeline_runs\stage04_update_test
```

ผลลัพธ์สำคัญ:

- records: 194,231
- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- stroke prevalence: 0.0711
- temporal-complete patients: 13
- temporal-complete stroke patients: 1
- temporal-complete non-stroke patients: 12
- high-missing variables >=50%: 9
- leakage audit passed: true
- sensitivity analysis recommended: true
- acceptance checks: 6/6 ผ่าน

## ข้อควรระวัง

- Stage 04 ไม่ควรแก้ไขข้อมูลหรือสร้าง feature
- strict paper windows ต้องยังเป็น baseline หลัก แม้จะ recommend sensitivity analysis เพิ่ม
- sensitivity analysis เป็นข้อเสนอเชิง validation/modeling ไม่ใช่การเปลี่ยน default method ของ paper
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push

## สถานะ

Implemented และทดสอบผ่านแล้ว
