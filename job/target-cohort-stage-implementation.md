# งาน: Update Stage 02 Target and Cohort

## เป้าหมาย

อัปเดต `src/target_cohort.py` ให้ทำ Stage 02 ตาม `docs/pipeline/02-target-and-cohort.md` ล่าสุด และผูกกับวิธีของงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` ให้ชัดขึ้น

Stage นี้เป็นจุดกัน data leakage หลักของ pipeline เพราะเป็นขั้นที่กำหนด `reference date` และตัด records หลัง reference date ก่อนส่งต่อให้ cleaning, EDA, feature engineering และ modeling

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/target_cohort.py`
- `docs/pipeline/02-target-and-cohort.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- method section: Data Selection
- stroke ICD-10 range `I60-I68`
- stroke reference rule: first stroke event date
- non-stroke reference rule: last clinical visit date
- formula ของ `months_before_reference`

เพิ่ม window metadata:

- `FIRST`: 21-9 เดือนก่อน `reference date`
- `MID`: 18-6 เดือนก่อน `reference date`
- `LAST`: 15-3 เดือนก่อน `reference date`
- ทุก window ใช้ boundary แบบ inclusive ตามสเปก pipeline
- จากภาพใน paper windows ทั้งสามเป็น overlapping windows ไม่ใช่ exclusive bins
- record เดียวอาจต้องถูก represent ในหลาย windows เช่น 12 เดือนก่อน reference date อยู่ใน FIRST, MID และ LAST

เพิ่มข้อมูลใน patient-level cohort:

- `stroke_event_count`
- `stroke_event_sources`
- `followup_days_before_reference`
- `reference_rule`

เพิ่ม audit/report ใหม่:

- `reference_date_audit.csv`
- `window_distribution_report.csv`
- `temporal_completeness_summary.csv`
- `target_cohort_acceptance_checks.csv`

เพิ่ม summary fields ใน `target_cohort_summary.json`:

- `paper_reference`
- `temporal_windows`
- `reference_date_audit_passed`
- `records_in_paper_windows`
- `patients_in_any_paper_window`
- `acceptance_checks_passed`
- `acceptance_checks_total`
- `acceptance_passed`

## Output จาก Stage 02

Default output directory:

```text
output/target_cohort_output
```

ไฟล์ที่ Stage 02 สร้าง:

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `temporal_completeness_summary.csv`
- `cohort_attrition_report.csv`
- `reference_date_audit.csv`
- `window_distribution_report.csv`
- `target_cohort_acceptance_checks.csv`
- `target_cohort_summary.json`
- `target_cohort_report.md`

## Acceptance Checks

`target_cohort_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- stroke patients ใช้ first stroke event date เป็น `reference_date`
- non-stroke patients ใช้ last clinical visit date เป็น `reference_date`
- ไม่มี records หลัง `reference_date`
- ใช้ paper-default windows `FIRST/MID/LAST`
- รองรับ overlapping window membership ตามภาพใน paper
- attrition report มีขั้น `temporal_complete`
- temporal-complete cohort ถูก report แยกจาก cohort ทั้งหมด

## วิธีรัน

ใช้ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.target_cohort
```

ระบุ output directory แยก:

```powershell
.\.venv\Scripts\python.exe -m src.target_cohort --output-dir output/pipeline_runs/stage02_update_test
```

ระบุ column mapping เอง:

```powershell
.\.venv\Scripts\python.exe -m src.target_cohort --patient-id-col hn --visit-date-col vstdate --principal-dx-col PrincipleDiagnosis --comorbidity-dx-col ComorbidityDiagnosis
```

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\target_cohort.py
```

ผลลัพธ์: ผ่าน

รัน Stage 02:

```powershell
.\.venv\Scripts\python.exe -m src.target_cohort --output-dir output/pipeline_runs/stage02_update_test
```

ผลลัพธ์สำคัญ:

- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13
- records in FIRST/MID/LAST windows: 44,977
- patients in any paper window: 11,787
- no post-reference records: true
- reference date audit passed: true
- acceptance checks: 6/6 ผ่าน

## ข้อควรระวัง

- Stage 02 ยังไม่ clean clinical values เชิงลึก หน้าที่นั้นอยู่ใน Stage 03
- Stage 02 ต้องไม่ใช้ข้อมูลหลัง `reference_date` ใน output ที่ส่งต่อ
- หมายเหตุสำคัญจากการทบทวนภาพ paper: implementation ปัจจุบันควรถูกตรวจต่อว่า `window` เป็น label เดียวหรือ long-format overlapping membership ถ้ายังเป็น label เดียวต้องแก้โค้ด Stage 02/05 ต่อ
- temporal-complete cohort น้อยมากในข้อมูลจริงปัจจุบัน จึงควรรายงาน attrition ชัดเจน และค่อยทำ sensitivity analysis ในขั้น validation/analysis หากต้องการใช้ window อื่น
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push

## สถานะ

Implemented และทดสอบผ่านแล้ว
