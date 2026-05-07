# งาน: Implement Stage 04 Exploratory Data Analysis

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/04-eda.md` เพื่อประเมินความพร้อมของข้อมูลสำหรับ temporal stroke-risk prediction โดยเน้น class imbalance, missingness, visit coverage, temporal window coverage, clinical distributions และ leakage audit

## ไฟล์โค้ดที่สร้าง

- `src/eda.py`

## สิ่งที่โค้ดทำ

`src/eda.py` เป็น CLI/module แยกสำหรับ Stage 04:

- โหลด cleaned pre-reference records จาก Stage 03
- โหลด patient-level cohort และ temporal completeness flags จาก Stage 02
- สร้าง class imbalance table ระดับ patient
- สร้าง visit frequency ต่อ patient
- สรุป distribution ของ visits ต่อ patient
- สร้าง visit count ต่อ temporal window
- สรุป time gap ระหว่าง visits
- สร้าง missingness summary:
  - ราย variable
  - แยก stroke/non-stroke
  - แยก FIRST/MID/LAST window
- สรุป temporal coverage และจำนวน temporal-complete patients
- สร้าง descriptive statistics ของ clinical variables แยก stroke/non-stroke
- ตรวจ leakage เบื้องต้นว่าไม่มี visit date หลัง reference date
- สร้าง markdown และ JSON summary report

## วิธีรัน

ใช้ค่า default:

```powershell
python -m src.eda
```

ระบุ input/output เอง:

```powershell
python -m src.eda --records-path output/data_cleaning_output/cleaned_pre_reference_records.csv --cohort-path output/target_cohort_output/patient_level_cohort.csv --output-dir output/eda_output
```

## Output

Default output directory:

```text
output/eda_output
```

ไฟล์ที่สร้าง:

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

## Acceptance Criteria

- มี stroke/non-stroke count ระดับ patient
- มี visit coverage แยก FIRST/MID/LAST
- ระบุ variables ที่ missing สูง
- ระบุผลกระทบของ strict temporal completeness ต่อ sample size
- ยืนยันว่า EDA ไม่ใช้ post-reference records

## สถานะ

Implemented แล้วเป็น module แยก สามารถใช้ output จาก Stage 02/03 ได้โดยตรง และ output พร้อมใช้ประกอบการตัดสินใจใน Stage 05 feature engineering

