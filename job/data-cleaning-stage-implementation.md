# งาน: Implement Stage 03 Data Cleaning

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/03-data-cleaning.md` เพื่อทำความสะอาด pre-reference clinical records ที่ผ่าน Stage 02 แล้ว โดยยังรักษาหลักการไม่ใช้ post-reference data ก่อนส่งต่อไป EDA และ feature engineering

## ไฟล์โค้ดที่สร้าง

- `src/data_cleaning.py`

## สิ่งที่โค้ดทำ

`src/data_cleaning.py` เป็น CLI/module แยกสำหรับ Stage 03:

- โหลด pre-reference records จาก Stage 02
- standardize column names ให้ใช้ง่ายขึ้น เช่น `hn` เป็น `patient_id`, `vstdate` เป็น `visit_date`, `HDL` เป็น `hdl`
- de-identification โดย drop direct/quasi identifier ที่ไม่จำเป็น เช่น `ตำบล`
- แปลง date columns เป็น datetime
- แปลง numeric columns เป็น numeric type
- drop exact duplicate rows
- normalize diagnosis fields เป็น ICD token columns:
  - `principal_diagnosis_normalized`
  - `comorbidity_diagnosis_normalized`
- enforce binary flag encoding `{0,1}` สำหรับ smoking, drinking, AF, disease flags และ medication flags
- ตรวจ plausible ranges ของ clinical variables เช่น blood pressure, lipid labs, FBS, BMI, eGFR, creatinine
- แทน implausible values ด้วย missing value และบันทึกใน cleaning log
- ตรวจซ้ำว่า output ไม่มี post-reference records

## วิธีรัน

ใช้ค่า default โดยอ่านจาก Stage 02 output:

```powershell
python -m src.data_cleaning
```

ระบุ input/output เอง:

```powershell
python -m src.data_cleaning --input-path output/target_cohort_output/pre_reference_records_with_windows.csv --output-dir output/data_cleaning_output
```

ถ้าต้องการเก็บ direct identifier columns ไว้ชั่วคราวเพื่อ audit:

```powershell
python -m src.data_cleaning --keep-direct-identifiers
```

## Output

Default output directory:

```text
output/data_cleaning_output
```

ไฟล์ที่สร้าง:

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

## Acceptance Criteria

- output ไม่มี direct/quasi identifier ที่ไม่จำเป็น เช่น `ตำบล`
- date columns อยู่ในรูปที่ใช้คำนวณ temporal windows ต่อได้
- binary flags มีเฉพาะ `0`, `1` หรือ missing
- implausible clinical values ถูก set เป็น missing และมี log
- output ยังไม่มี records หลัง reference date

## สถานะ

Implemented แล้วเป็น module แยก สามารถใช้ output จาก `src.target_cohort` เป็น input โดยตรง และ output พร้อมส่งต่อ Stage 04 EDA หรือ Stage 05 feature engineering

