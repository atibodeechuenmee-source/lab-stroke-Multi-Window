# งาน: Update Stage 03 Data Cleaning

## เป้าหมาย

อัปเดต `src/data_cleaning.py` ให้ทำ Stage 03 ตาม `docs/pipeline/03-data-cleaning.md` ล่าสุด และรักษาหลักสำคัญจากงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

Stage นี้ทำความสะอาดเฉพาะ `pre-reference records` จาก Stage 02 เท่านั้น โดยต้องไม่สร้าง target leakage ใหม่ และต้องยืนยันซ้ำว่าไม่มี records หลัง `reference_date`

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/data_cleaning.py`
- `docs/pipeline/03-data-cleaning.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- method section: Data Preprocessing
- cleaning principle: clean pre-reference EHR records without introducing post-reference leakage
- stroke ICD-10 range `I60-I68`

เพิ่ม required output column audit:

- `patient_id`
- `visit_date`
- `reference_date`
- `stroke`
- `window`

เพิ่ม validation/report ใหม่:

- `required_output_columns_report.csv`
- `binary_validation_report.csv`
- `leakage_audit_after_cleaning.csv`
- `data_cleaning_acceptance_checks.csv`

ปรับ diagnosis normalization:

- สร้าง normalized ICD columns เหมือนเดิม
- เพิ่มตัวชี้วัดว่า stroke ICD signal สูญหายหรือไม่
- ใช้เกณฑ์ preservation ที่ถูกต้องกว่าเดิม: normalization ผ่านถ้าไม่มี ICD `I60-I68` ที่เคยพบก่อน clean หายไปหลัง clean
- อนุญาตให้ tokenization พบ ICD เพิ่มจากข้อความเดิมได้ เพราะเป็นการดึง token จาก raw text ไม่ใช่การสร้าง target ใหม่

เพิ่ม summary fields ใน `cleaning_report.json`:

- `paper_reference`
- `required_output_columns_available`
- `required_output_columns_missing`
- `diagnosis_stroke_signal_preserved`
- `acceptance_checks_passed`
- `acceptance_checks_total`
- `acceptance_passed`

## Output จาก Stage 03

Default output directory:

```text
output/data_cleaning_output
```

ไฟล์ที่ Stage 03 สร้าง:

- `cleaned_pre_reference_records.csv`
- `cleaning_report.json`
- `cleaning_report.md`
- `cleaning_log.csv`
- `data_cleaning_acceptance_checks.csv`
- `required_output_columns_report.csv`
- `binary_validation_report.csv`
- `leakage_audit_after_cleaning.csv`
- `missing_summary_after_cleaning.csv`
- `range_summary_after_cleaning.csv`
- `binary_flag_encoding_map.csv`
- `diagnosis_normalization_report.csv`
- `column_standardization_report.csv`
- `deidentification_report.csv`

## Acceptance Checks

`data_cleaning_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- cleaned data ยังมี required columns สำหรับ stage ถัดไปครบ
- ไม่มี records หลัง `reference_date`
- binary columns เหลือเฉพาะ `0`, `1`, หรือ missing
- implausible clinical values ถูก log
- diagnosis normalization ไม่ทำให้ ICD-10 `I60-I68` signal หาย
- cleaning ไม่สร้าง target leakage ใหม่

## วิธีรัน

ใช้ค่า default โดยอ่านจาก Stage 02 output:

```powershell
.\.venv\Scripts\python.exe -m src.data_cleaning
```

ระบุ input/output เอง:

```powershell
.\.venv\Scripts\python.exe -m src.data_cleaning --input-path output\pipeline_runs\stage02_update_test\pre_reference_records_with_windows.csv --output-dir output\pipeline_runs\stage03_update_test
```

ถ้าต้องการเก็บ direct identifier columns ไว้ชั่วคราวเพื่อ audit:

```powershell
.\.venv\Scripts\python.exe -m src.data_cleaning --keep-direct-identifiers
```

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\data_cleaning.py
```

ผลลัพธ์: ผ่าน

รัน Stage 03:

```powershell
.\.venv\Scripts\python.exe -m src.data_cleaning --input-path output\pipeline_runs\stage02_update_test\pre_reference_records_with_windows.csv --output-dir output\pipeline_runs\stage03_update_test
```

ผลลัพธ์สำคัญ:

- rows before cleaning: 194,231
- rows after cleaning: 194,231
- columns after cleaning: 37
- duplicate rows removed: 0
- direct identifier columns dropped: `ตำบล`
- range-invalid values set missing: 3
- binary-invalid values set missing: 69,612
- no post-reference records: true
- required output columns available: 5
- required output columns missing: none
- diagnosis stroke signal preserved: true
- acceptance checks: 6/6 ผ่าน

Diagnosis normalization audit:

- `principal_diagnosis`: stroke hits before 951, after 1,176, lost 0
- `comorbidity_diagnosis`: stroke hits before 63, after 130, lost 0

จำนวนหลัง normalization มากขึ้นเพราะ tokenization ดึง ICD tokens จากข้อความ diagnosis ได้ชัดขึ้น แต่ไม่มี stroke ICD ที่เคยพบเดิมหายไป

## ข้อควรระวัง

- Stage 03 ไม่ควรสร้าง `reference_date`, target label หรือ temporal windows ใหม่เอง เพราะเป็นหน้าที่ของ Stage 02
- Stage 03 ต้องทำงานเฉพาะ records ที่ Stage 02 ตัด post-reference ออกแล้ว
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push

## สถานะ

Implemented และทดสอบผ่านแล้ว
