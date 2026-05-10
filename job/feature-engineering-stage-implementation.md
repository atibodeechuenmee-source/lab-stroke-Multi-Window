# งาน: Update Stage 05 Feature Engineering

## เป้าหมาย

อัปเดต `src/feature_engineering.py` ให้ทำ Stage 05 ตาม `docs/pipeline/05-feature-engineering.md` ล่าสุด และทำให้ตรวจสอบได้ชัดเจนว่า feature tables สร้างตาม blueprint ของงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` แค่ไหน

Stage นี้เป็นหัวใจของโปรเจกต์ เพราะสร้างทั้ง `single-shot baseline` และ temporal Extract Set 1/2/3 เพื่อใช้เปรียบเทียบว่า temporal features เพิ่ม predictive value เหนือ baseline หรือไม่

หมายเหตุจากการทบทวนภาพใน paper: FIRST/MID/LAST เป็น overlapping windows ดังนั้น record เดียวอาจ contribute ให้หลาย window ได้ การสร้าง features ต้องอิง window membership แบบ long format หรือ multi-hot ไม่ใช่เลือก window เดียวแบบ exclusive

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/feature_engineering.py`
- `docs/pipeline/05-feature-engineering.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- method section: Feature Extraction
- single-shot role: required baseline comparator
- temporal windows: `FIRST`, `MID`, `LAST`
- paper target feature counts:
  - Extract Set 1: 35
  - Extract Set 2: 115
  - Extract Set 3: 121

เพิ่ม audit/report ใหม่:

- `single_shot_audit.csv`
- `tc_hdl_audit.csv`
- `temporal_window_usage_report.csv`
- `feature_set_comparison.csv`
- `feature_engineering_acceptance_checks.csv`

เพิ่มการตรวจ `TC:HDL`:

- ตรวจว่ามี `tc_hdl_ratio` อยู่เดิมหรือไม่
- ถ้ายังไม่มีให้คำนวณจาก `cholesterol / hdl`
- ป้องกันการหารด้วยศูนย์
- รายงานจำนวน non-null หลังคำนวณ

เพิ่ม single-shot audit:

- ตรวจว่า single-shot มีหนึ่งแถวต่อ patient
- ตรวจว่าใช้ latest pre-reference visit ต่อ patient

เพิ่ม feature count comparison:

- เทียบ actual feature count กับ paper target 35/115/121
- รายงานความต่างใน `feature_set_comparison.csv`
- บังคับ acceptance ให้ผ่านเฉพาะเมื่อ actual feature count ตรง paper target ทั้ง 3 ชุด

เพิ่ม summary fields ใน `feature_engineering_report.json`:

- `paper_reference`
- `paper_target_feature_counts`
- `extract_set_1_feature_count`
- `extract_set_2_feature_count`
- `extract_set_3_feature_count`
- `feature_dictionary_rows`
- `acceptance_checks_passed`
- `acceptance_checks_total`
- `acceptance_passed`

## Output จาก Stage 05

Default output directory:

```text
output/feature_engineering_output
```

ไฟล์ที่ Stage 05 สร้าง:

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- `temporal_completeness_flags.csv`
- `feature_dictionary.csv`
- `feature_generation_log.csv`
- `feature_engineering_exclusions.csv`
- `single_shot_audit.csv`
- `tc_hdl_audit.csv`
- `temporal_window_usage_report.csv`
- `feature_set_comparison.csv`
- `feature_engineering_acceptance_checks.csv`
- `feature_engineering_report.json`
- `feature_engineering_report.md`

## Acceptance Checks

`feature_engineering_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- single-shot ใช้ latest pre-reference record
- temporal features ใช้เฉพาะ `FIRST/MID/LAST`
- ไม่มี post-reference records ถูกใช้
- feature dictionary trace origin ได้
- Extract Set 1/2/3 ถูกสร้างแยกกัน
- feature counts ถูกเทียบกับ paper targets
- `TC:HDL` พร้อมใช้งานและป้องกัน divide-by-zero
- FIRST/MID/LAST ต้องรองรับ overlapping window membership

## วิธีรัน

ใช้ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.feature_engineering
```

ระบุ input/output เอง:

```powershell
.\.venv\Scripts\python.exe -m src.feature_engineering --records-path output\pipeline_runs\stage03_update_test\cleaned_pre_reference_records.csv --output-dir output\pipeline_runs\stage05_update_test
```

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\feature_engineering.py
```

ผลลัพธ์: ผ่าน

รัน Stage 05:

```powershell
.\.venv\Scripts\python.exe -m src.feature_engineering --records-path output\pipeline_runs\stage03_update_test\cleaned_pre_reference_records.csv --output-dir output\pipeline_runs\stage05_update_test
```

ผลลัพธ์สำคัญ:

- patients: 13,635
- single-shot rows: 13,635
- temporal-complete patients: 13
- Extract Set 1: 13 rows x 37 columns
- Extract Set 2: 13 rows x 117 columns
- Extract Set 3: 13 rows x 123 columns
- excluded patients from temporal sets: 13,622
- no post-reference records: true
- feature dictionary rows: 177
- acceptance checks: 7/7 ผ่าน

Feature count comparison:

- Extract Set 1 actual features: 35, paper target: 35
- Extract Set 2 actual features: 115, paper target: 115
- Extract Set 3 actual features: 121, paper target: 121

หมายเหตุ: รอบล่าสุดปรับ schema ให้ตรงกับสูตรนับของ paper แล้ว โดย Set 1 = `10 numeric x 3 windows + 5 static`, Set 2 = `11 descriptors x 10 numeric + 5 static`, และ Set 3 = `Set 2 + 6 risk factors`

ข้อควร follow-up: แม้ feature count จะตรง paper แล้ว ต้องตรวจและแก้ Stage 02/05 ต่อให้ records ในช่วง overlap ถูกใช้ในทุก matching window ตามภาพ paper

## ข้อควรระวัง

- single-shot baseline ต้องคงไว้เสมอ เพราะเป็น comparator หลักของ paper
- temporal Extract Set 1/2/3 ต้องใช้เฉพาะ temporal-complete patients ตาม strict FIRST/MID/LAST baseline
- temporal-complete cohort ในข้อมูลจริงมีน้อยมาก จึงต้องส่งต่อข้อจำกัดนี้ไป Stage 06-08
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push

## สถานะ

Implemented และทดสอบผ่านแล้ว
