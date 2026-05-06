# งาน: Implement Stage 01 Raw Data Audit

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/01-raw-data.md` สำหรับตรวจสอบ raw EHR data ก่อนเข้าสู่ขั้นตอน cleaning และ cohort construction

Stage นี้ต้องเป็น read-only ต่อ raw data และทำหน้าที่สร้าง audit artifacts เพื่อบอกว่า dataset มี column, data type, missingness, ICD-10 stroke codes และ longitudinal visit coverage เพียงพอสำหรับ temporal feature engineering หรือไม่

## ไฟล์โค้ดที่สร้าง

- `src/raw_data.py`

## สิ่งที่โค้ดทำ

`src/raw_data.py` เป็น CLI/module สำหรับ Stage 01 โดยทำงานดังนี้:

- โหลด raw data จาก Excel หรือ CSV
- สร้าง raw column list
- สร้าง schema summary พร้อม dtype, missing count, missing percent, unique count และ example values
- สร้าง missingness summary
- ตรวจ required column availability ตาม paper เช่น patient id, visit date, diagnosis, labs, medication และ risk-factor flags
- ตรวจ visit coverage ต่อ patient เช่น record count, first visit, last visit และ follow-up days
- ตรวจ ICD-10 availability สำหรับ stroke codes `I60-I68`
- ตรวจ range เบื้องต้นของ clinical variables เช่น blood pressure, HDL, LDL, FBS, BMI, eGFR และ creatinine
- สร้าง JSON และ markdown report สำหรับอ่านสรุปเร็ว

## วิธีรัน

ใช้ค่า default:

```powershell
python -m src.raw_data
```

ระบุ raw file และ output directory เอง:

```powershell
python -m src.raw_data --raw-path data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx --output-dir output/raw_data_output
```

ระบุชื่อ column เองถ้าข้อมูลเปลี่ยน:

```powershell
python -m src.raw_data --patient-id-col hn --visit-date-col vstdate --principal-dx-col PrincipleDiagnosis --comorbidity-dx-col ComorbidityDiagnosis
```

## Output

Default output directory:

```text
output/raw_data_output
```

ไฟล์ที่สร้าง:

- `raw_column_list.csv`
- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `raw_range_summary.csv`
- `visit_coverage_summary.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_report.json`
- `raw_data_report.md`

## Acceptance Criteria

- ไม่แก้ไข raw file ใน `data/raw`
- ต้องพบ patient identifier เช่น `hn`
- ต้องพบ visit date เช่น `vstdate`
- ต้องพบ diagnosis fields สำหรับ map ICD-10 `I60-I68`
- ต้องรายงาน missing expected columns อย่างชัดเจน
- ต้องสร้าง visit coverage summary เพื่อใช้ตัดสินใจเรื่อง temporal windows ใน stage ถัดไป

## สถานะ

Implemented แล้วเป็น module แยกจาก `src/temporal_pipeline.py` เพื่อให้รัน Stage 01 ได้โดยตรง และสามารถใช้ output เป็น input/context ให้ Stage 02-05 ต่อได้

