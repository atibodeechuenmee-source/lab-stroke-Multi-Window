# งาน: Stage 00 และ Temporal Pipeline Orchestrator

## เป้าหมาย

อัปเดต `src/temporal_pipeline.py` ให้ทำหน้าที่เป็น Stage 00 ของโปรเจกต์อย่างชัดเจน ไม่ใช่เป็นแค่ไฟล์เรียก stage อื่น ๆ เท่านั้น

Stage 00 มีหน้าที่กำหนด contract กลางของทั้ง pipeline ตามงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction` เพื่อให้ทุก run ของ pipeline มี metadata ที่ตรวจสอบได้ว่าใช้กติกาเดียวกับ paper หรือไม่

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

## สิ่งที่ Stage 00 ทำในโค้ด

`src/temporal_pipeline.py` เพิ่มข้อมูลกำกับ pipeline ระดับภาพรวม ได้แก่:

- ชื่องานวิจัยหลักที่ใช้เป็น blueprint
- path ของ paper PDF, ไฟล์แปลไทย, research note และ pipeline overview
- ICD-10 stroke definition `I60-I68`
- temporal windows ตาม paper:
  - `FIRST`: 21-9 เดือนก่อน `reference date`
  - `MID`: 18-6 เดือนก่อน `reference date`
  - `LAST`: 15-3 เดือนก่อน `reference date`
- FIRST/MID/LAST เป็น overlapping retrospective windows ตามภาพใน paper ไม่ใช่ exclusive bins
- feature sets:
  - `single_shot_baseline`
  - `extract_set_1`
  - `extract_set_2`
  - `extract_set_3`
- metrics หลัก: sensitivity, specificity, `G-Mean`
- leakage guardrails:
  - stroke patient ใช้ first stroke event เป็น `reference date`
  - non-stroke patient ใช้ last clinical visit เป็น `reference date`
  - ลบ records หลัง `reference date`
  - temporal features ต้องมาจาก retrospective windows เท่านั้น
- stage sequence ตั้งแต่ Stage 00 ถึง Stage 09 พร้อม mapping ไปยังไฟล์เอกสารและ module

## ฟังก์ชันใหม่

### `build_stage_00_overview()`

สร้าง metadata สำหรับ Stage 00 แล้วบันทึกลง `pipeline_manifest.json` ใน key:

```json
"stage_00_pipeline_overview"
```

metadata นี้ช่วยให้ตรวจได้ว่า run ปัจจุบันอ้างอิง paper, เอกสาร, temporal windows, feature sets และ stage order ครบหรือไม่

### `evaluate_stage_00_acceptance()`

สรุป acceptance checks ระดับ pipeline จากผลลัพธ์ของ stage ที่รันแล้ว แล้วบันทึกลง manifest ใน key:

```json
"stage_00_acceptance_checks"
```

checks ที่ตรวจ ได้แก่:

- raw input file มีอยู่จริง
- paper artifacts มีอยู่ครบ
- stage documents มีอยู่ครบ
- FIRST/MID/LAST windows ถูก register ครบ
- ไม่มี post-reference leakage จาก Stage 02/03/05
- มี `single-shot baseline` เป็น comparator
- metrics หลักถูก register ครบ
- validation รองรับ McNemar's test เมื่อรันถึง Stage 08

## Flow การรัน

รันถึง Stage 05:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling
```

รันถึง Stage 08:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline
```

รันด้วย output directory แยก:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling --output-dir output/pipeline_runs/orchestrator_test
```

## Output หลัก

Default output:

```text
output/pipeline_runs/temporal_pipeline/
```

โครง output:

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

`pipeline_manifest.json` ตอนนี้จะมีข้อมูล Stage 00 เพิ่มขึ้น เพื่อใช้เป็นหลักฐานว่า run นี้ตั้งค่าตาม paper ก่อนเริ่ม Stage 01-08

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\temporal_pipeline.py
```

ผลลัพธ์: ผ่าน

ตรวจ Stage 00 metadata แบบไม่ต้องรันข้อมูลทั้ง pipeline:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from src.temporal_pipeline import PipelineConfig, stage_dirs, build_stage_00_overview; c=PipelineConfig(output_dir=Path('output/pipeline_runs/stage00_metadata_check')); o=build_stage_00_overview(c, stage_dirs(c.output_dir)); print(o['stroke_icd10_definition'], sorted(o['temporal_windows'].keys()), len(o['stage_sequence']))"
```

ผลลัพธ์:

```text
I60-I68 ['FIRST', 'LAST', 'MID'] 10
```

หมายเหตุ: การรัน pipeline จริงแบบ `--skip-modeling` ใช้เวลานานกว่า timeout รอบตรวจล่าสุด จึงใช้ `py_compile` และ metadata import check เป็น verification ของการแก้ Stage 00 ในรอบนี้

## ข้อควรระวัง

- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push
- `.venv/` และ `src/__pycache__/` เป็น environment/runtime artifacts ไม่ควร commit
- Stage 00 เป็น control/manifest layer ไม่ควรสร้าง target, features หรือ model เอง เพราะ logic เหล่านั้นอยู่ใน Stage 01-08 แล้ว

## สถานะ

Implemented แล้ว
