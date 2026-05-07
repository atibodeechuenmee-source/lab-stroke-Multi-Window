# งาน: Implement Stage 02 Target and Cohort

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/02-target-and-cohort.md` เพื่อสร้าง patient-level cohort, stroke target, reference date, pre-reference records, temporal window assignment และ temporal completeness flags

Stage นี้เป็นจุดกัน data leakage ที่สำคัญที่สุดของ pipeline เพราะต้องตัด records หลัง stroke event หรือหลัง reference date ออกก่อนสร้าง features

## ไฟล์โค้ดที่สร้าง

- `src/target_cohort.py`

## สิ่งที่โค้ดทำ

`src/target_cohort.py` ทำงานเป็น CLI/module แยกสำหรับ Stage 02:

- โหลด raw หรือ lightly standardized EHR records จาก Excel/CSV
- ตรวจ required columns เช่น patient id, visit date และ diagnosis fields
- identify stroke event จาก ICD-10 `I60-I68`
- สร้าง patient-level label:
  - `stroke = 1` ถ้าพบ stroke event อย่างน้อยหนึ่งครั้ง
  - `stroke = 0` ถ้าไม่พบ stroke event
- กำหนด `reference_date`:
  - stroke patient ใช้ first stroke event date
  - non-stroke patient ใช้ last visit date
- ลบ post-reference records เพื่อป้องกัน leakage
- คำนวณ `days_before_reference` และ `months_before_reference`
- assign temporal windows:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- ตรวจ temporal completeness จาก visit coverage และ core clinical columns
- สร้าง cohort attrition report
- สร้าง quality-check summary เพื่อยืนยัน acceptance criteria

## วิธีรัน

ใช้ค่า default:

```powershell
python -m src.target_cohort
```

ระบุ input/output เอง:

```powershell
python -m src.target_cohort --input-path data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx --output-dir output/target_cohort_output
```

ระบุชื่อ columns เองถ้าข้อมูลเปลี่ยน:

```powershell
python -m src.target_cohort --patient-id-col hn --visit-date-col vstdate --principal-dx-col PrincipleDiagnosis --comorbidity-dx-col ComorbidityDiagnosis
```

## Output

Default output directory:

```text
output/target_cohort_output
```

ไฟล์ที่สร้าง:

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `cohort_attrition_report.csv`
- `target_cohort_summary.json`
- `target_cohort_report.md`

## Acceptance Criteria

- ไม่มี records ที่ visit date มากกว่า reference date ใน output
- stroke patient ใช้ first stroke date เป็น reference date
- non-stroke patient ใช้ last visit date เป็น reference date
- มี FIRST/MID/LAST window assignment สำหรับ records ที่อยู่ในช่วง paper
- มี temporal completeness flags แยกตาม window
- มี cohort attrition report เพื่อบอกจำนวน patients/records ที่ถูกคัดออกในแต่ละขั้น

## สถานะ

Implemented แล้วเป็น module แยกจาก `src/temporal_pipeline.py` และสามารถใช้ output เป็น input ของ Stage 05 feature engineering ได้

