# งาน: Update Stage 01 Raw Data Audit

## เป้าหมาย

อัปเดต `src/raw_data.py` ให้ทำ Stage 01 ตาม `docs/pipeline/01-raw-data.md` ล่าสุด และยึดงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` เป็น blueprint มากขึ้น

Stage นี้ยังคงเป็น read-only ต่อ raw data ต้นทาง แต่เพิ่มหลักฐานตรวจสอบย้อนกลับ เช่น file integrity, data dictionary, acceptance checks และสรุป visit coverage เพื่อใช้ตัดสินความพร้อมสำหรับ temporal windows ใน Stage 02-05

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/raw_data.py`
- `docs/pipeline/01-raw-data.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- data source ตาม paper
- จำนวน records/patients ที่ paper รายงาน
- raw attributes ที่ paper รายงาน
- stroke ICD-10 range `I60-I68`

เพิ่ม raw file integrity:

- file size
- modified time
- SHA-256 hash
- read-only policy flag

เพิ่ม expected field details:

- category ของแต่ละ field เช่น identifier, temporal, diagnosis, lab, medication
- paper role ของ field
- stage หรือ feature set ที่ต้องใช้ field นั้น

เพิ่ม output ใหม่:

- `raw_data_dictionary.csv`
- `visit_coverage_overview.csv`
- `raw_data_acceptance_checks.csv`
- `raw_file_integrity.json`

เพิ่ม summary fields ใน `raw_data_report.json`:

- `paper_reference`
- `raw_file_sha256`
- `raw_file_size_bytes`
- `missing_required_fields`
- `visit_coverage_patients`
- `acceptance_checks_passed`
- `acceptance_checks_total`
- `acceptance_passed`

## Output จาก Stage 01

Default output directory:

```text
output/raw_data_output
```

ไฟล์ที่ Stage 01 สร้าง:

- `raw_column_list.csv`
- `raw_data_dictionary.csv`
- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `raw_range_summary.csv`
- `visit_coverage_summary.csv`
- `visit_coverage_overview.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_acceptance_checks.csv`
- `raw_file_integrity.json`
- `raw_data_report.json`
- `raw_data_report.md`

## Acceptance Checks

`raw_data_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- raw file read-only policy
- พบ patient identifier
- พบ visit date
- พบ diagnosis column อย่างน้อยหนึ่งคอลัมน์
- ตรวจ ICD-10 `I60-I68`
- รายงาน missingness ของ expected fields
- รายงาน visit coverage

## วิธีรัน

ใช้ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data
```

ระบุ output directory แยก:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data --output-dir output/pipeline_runs/stage01_update_test
```

ระบุ column mapping เอง:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data --patient-id-col hn --visit-date-col vstdate --principal-dx-col PrincipleDiagnosis --comorbidity-dx-col ComorbidityDiagnosis
```

## ผลทดสอบล่าสุด

รันคำสั่ง:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\raw_data.py
```

ผลลัพธ์: ผ่าน

รัน Stage 01:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data --output-dir output/pipeline_runs/stage01_update_test
```

ผลลัพธ์สำคัญ:

- rows: 218,772
- columns: 30
- patients: 13,635
- required fields available: 29
- required fields missing: 0
- stroke ICD `I60-I68` record hits: 3,950
- visit coverage patients: 13,635
- acceptance checks: 7/7 ผ่าน
- raw file SHA-256: `f94057da8fe96844f1450985514f222c79964a827f6b0ded7740d622dbc8a13f`

## ข้อควรระวัง

- Stage 01 ไม่ clean, drop, overwrite หรือ mutate raw data
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push
- Stage 01 เป็น audit layer ก่อนสร้าง target/cohort ดังนั้นยังไม่ควรสร้าง `reference date` หรือ temporal features ในไฟล์นี้

## สถานะ

Implemented และทดสอบผ่านแล้ว
