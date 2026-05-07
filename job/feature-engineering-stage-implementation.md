# งาน: Implement Stage 05 Feature Engineering

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/05-feature-engineering.md` เพื่อสร้าง feature tables ระดับ patient สำหรับเปรียบเทียบ single-shot baseline กับ temporal feature models ตาม Extract Set 1/2/3 ของ paper

Stage นี้ใช้เฉพาะ cleaned pre-reference records จาก Stage 03 และ records ที่อยู่ใน temporal windows FIRST/MID/LAST สำหรับ temporal feature sets

## ไฟล์โค้ดที่สร้าง

- `src/feature_engineering.py`

## สิ่งที่โค้ดทำ

`src/feature_engineering.py` เป็น CLI/module แยกสำหรับ Stage 05:

- โหลด cleaned pre-reference records จาก Stage 03
- ตรวจว่าไม่มี record หลัง reference date
- คำนวณ `tc_hdl_ratio` ถ้ายังไม่มี โดยใช้ `cholesterol / hdl` และไม่หารด้วยศูนย์
- สร้าง single-shot baseline จาก latest pre-reference record ต่อ patient
- ตรวจ temporal completeness ตาม FIRST/MID/LAST และ core numerical variables
- สร้าง Extract Set 1:
  - window mean features สำหรับ clinical numerical variables
  - latest categorical features เช่น sex, AF, smoking, drinking
- สร้าง Extract Set 2:
  - statistical descriptors: mean, min, max, std, first, last, count
  - temporal descriptors: delta, slope, min/max/count differences ระหว่าง LAST และ FIRST
- สร้าง Extract Set 3:
  - เพิ่ม diabetes, hypertension, heart disease, statin, antihypertensive flag และ TC:HDL ratio
- สร้าง feature dictionary เพื่อระบุ source column, source window และ aggregation method
- สร้าง feature generation log และ exclusion report สำหรับ patients ที่ไม่ผ่าน temporal completeness

## วิธีรัน

ใช้ค่า default:

```powershell
python -m src.feature_engineering
```

ระบุ input/output เอง:

```powershell
python -m src.feature_engineering --records-path output/data_cleaning_output/cleaned_pre_reference_records.csv --output-dir output/feature_engineering_output
```

## Output

Default output directory:

```text
output/feature_engineering_output
```

ไฟล์ที่สร้าง:

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- `temporal_completeness_flags.csv`
- `feature_dictionary.csv`
- `feature_generation_log.csv`
- `feature_engineering_exclusions.csv`
- `feature_engineering_report.json`
- `feature_engineering_report.md`

## Acceptance Criteria

- ทุก feature table มีหนึ่งแถวต่อหนึ่ง patient
- single-shot baseline ใช้ latest pre-reference record เท่านั้น
- temporal features ใช้เฉพาะ records ใน FIRST/MID/LAST
- `tc_hdl_ratio` ไม่หารด้วยศูนย์
- feature dictionary ระบุ source window และ aggregation method
- exclusion report ระบุผู้ป่วยที่สร้าง temporal features ไม่ได้

## สถานะ

Implemented แล้วเป็น module แยก สามารถใช้ output จาก `src.data_cleaning` ได้โดยตรง และ output พร้อมเป็น input ของ Stage 06 modeling และ Stage 07 feature importance

