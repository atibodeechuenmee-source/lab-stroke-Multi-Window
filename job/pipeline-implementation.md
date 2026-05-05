# Pipeline Implementation

เอกสารนี้สรุปงาน pipeline ที่เพิ่มจากแผนใน `docs/pipeline/` เพื่อแยก workflow ออกเป็นขั้นตอนชัดเจนและรันซ้ำได้จาก command line

## Pipeline Documents

เพิ่มเอกสารแผนรายขั้นใน `docs/pipeline/`:

- `00-pipeline-overview.md`
- `01-raw-data.md`
- `02-target-and-cohort.md`
- `03-data-cleaning.md`
- `04-eda.md`
- `05-feature-engineering.md`
- `06-modeling.md`
- `07-feature-importance.md`
- `08-validation.md`
- `09-deployment-optional.md`

แต่ละไฟล์ใช้โครงสร้างเดียวกัน:

- Goal
- Inputs
- Steps
- Outputs
- Checks

## Code Added

### `src/pipeline_overview.py`

ใช้เป็น orchestrator สำหรับ pipeline overview:

- ตรวจ input/output ของแต่ละ stage
- รองรับ `--dry-run`
- รัน stage ที่มี production script แล้ว
- เขียน manifest การรันลง `output/pipeline_runs/`
- mark stage ที่ยังมีแค่แผนเป็น `not_implemented`

ตัวอย่าง:

```powershell
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --dry-run
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --stage raw-data
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --stage target-and-cohort
```

### `src/raw_data.py`

สร้างจาก `docs/pipeline/01-raw-data.md`:

- อ่าน raw Excel โดยไม่แก้ไฟล์ต้นฉบับ
- สร้าง schema summary
- สร้าง missing summary
- ตรวจ column availability สำหรับ target, cohort, cleaning และ feature engineering
- บันทึก report ลง `output/raw_data_output/`

ผลรันล่าสุด:

- rows: 218,772
- columns: 30
- missing required columns: none

### `src/target_cohort.py`

สร้างจาก `docs/pipeline/02-target-and-cohort.md`:

- แปลง `vstdate` เป็น datetime
- สร้าง `stroke_flag` จาก `PrincipleDiagnosis` ด้วย ICD-10 `I60-I69*` เพื่อใช้เป็น event marker ระดับ record
- สร้าง patient-level 90-day cohort พร้อม `index_date`, `event_date`, `days_to_event`, `stroke_3m`
- ใช้ `stroke_3m` เป็น target หลักสำหรับโจทย์ทำนายอนาคตระดับคนไข้
- สรุป excluded patients ที่ไม่เข้า cohort

ผลรันล่าสุด:

- record rows: 218,772
- record-level stroke prevalence: 2.36%
- patient-level 90-day cohort rows: 13,031
- patient-level 90-day stroke prevalence: 3.12%
- excluded patients: 604, reason `positive_outside_horizon`

## Outputs

เพิ่ม output ใหม่:

- `output/raw_data_output/raw_schema_summary.csv`
- `output/raw_data_output/raw_missing_summary.csv`
- `output/raw_data_output/column_availability_checklist.csv`
- `output/raw_data_output/raw_data_report.json`
- `output/raw_data_output/raw_data_report.md`
- `output/target_cohort_output/record_level_target.csv`
- `output/target_cohort_output/patient_level_90d_cohort.csv`
- `output/target_cohort_output/patient_level_90d_exclusions.csv`
- `output/target_cohort_output/target_cohort_summary.json`
- `output/target_cohort_output/target_cohort_report.md`
- `output/pipeline_runs/pipeline_manifest_*.json`

## Validation Commands

รันคำสั่งตรวจสอบแล้ว:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\src\pipeline_overview.py .\src\raw_data.py .\src\target_cohort.py
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --dry-run
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --stage raw-data
.\.venv\Scripts\python.exe .\src\pipeline_overview.py --stage target-and-cohort
```

## Notes

- ขั้น `data-cleaning` และ `deployment-optional` ยังเป็นแผน ยังไม่มี production script
- `target-and-cohort` stage แยกออกจาก `patient_level_prediction.py` เพื่อทำเฉพาะนิยาม target/cohort โดยไม่ train model
- `PrincipleDiagnosis` ใช้สร้าง target เท่านั้น และไม่ควรถูกใช้เป็น feature ของโมเดล
