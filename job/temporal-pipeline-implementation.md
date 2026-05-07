# งาน: Refactor Temporal Pipeline Orchestrator

## เป้าหมาย

ปรับ `src/temporal_pipeline.py` จากไฟล์ pipeline รวมที่มี logic ซ้ำ ให้เป็น orchestrator ที่เรียกใช้โค้ดจาก stage modules แยกโดยตรง

เหตุผลหลักคือให้ pipeline รวมและ stage แยกใช้ implementation ชุดเดียวกัน ลดความเสี่ยงที่กติกา target, cleaning, feature engineering, modeling หรือ validation จะต่างกันระหว่างไฟล์

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/temporal_pipeline.py`
- `src/raw_data.py`
- `src/target_cohort.py`
- `src/data_cleaning.py`
- `src/eda.py`
- `src/feature_engineering.py`
- `src/modeling.py`
- `src/feature_importance.py`
- `src/validation.py`

## สิ่งที่เปลี่ยน

`src/temporal_pipeline.py` ตอนนี้ทำหน้าที่เป็น orchestrator เท่านั้น:

- สร้าง output directory แยกตาม stage ใต้ pipeline run เดียวกัน
- เรียก `run_raw_data_audit()` สำหรับ Stage 01
- เรียก `run_target_cohort()` สำหรับ Stage 02
- เรียก `run_data_cleaning()` สำหรับ Stage 03
- เรียก `run_eda()` สำหรับ Stage 04
- เรียก `run_feature_engineering()` สำหรับ Stage 05
- ถ้าไม่ใช้ `--skip-modeling` จะเรียก Stage 06-08 ต่อ:
  - `run_modeling()`
  - `run_feature_importance()`
  - `run_validation()`
- เขียน `pipeline_manifest.json` ที่รวม summary ของแต่ละ stage

## วิธีรัน

รันถึง Stage 05:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling
```

รันถึง Stage 08:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline
```

รันทดสอบใน output directory แยก:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling --output-dir output/pipeline_runs/orchestrator_test
```

## ผลทดสอบล่าสุด

รันทดสอบด้วย:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling --output-dir output/pipeline_runs/orchestrator_test
```

ผลลัพธ์:

- Stage 01-05 รันสำเร็จ
- raw rows: 218,772
- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13
- single-shot rows: 13,635
- Extract Set 1: 13 rows x 36 columns
- Extract Set 2: 13 rows x 266 columns
- Extract Set 3: 13 rows x 272 columns
- leakage audit ผ่าน (`no_post_reference_records = true`)

## Output

Default output:

```text
output/pipeline_runs/temporal_pipeline/
```

โครง output ใหม่:

```text
raw_data_output/
target_cohort_output/
data_cleaning_output/
eda_output/
feature_engineering_output/
model_output/
feature_importance_output/
validation_output/
pipeline_manifest.json
```

## ข้อควรระวัง

- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push
- การรันจาก raw `.xlsx` ต้องมี `openpyxl` ใน Python environment
- ถ้า temporal cohort ยังมี positive class น้อยเกินไป Stage 06-08 จะสร้างรายงานแบบ `skipped` ตามเหตุผลเชิงข้อมูล

## สถานะ

Implemented แล้ว และทดสอบผ่านแบบ `--skip-modeling` ด้วย output directory แยก
