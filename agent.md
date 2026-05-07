# Agent Guide

เอกสารนี้คือคู่มือสำหรับ AI agent หรือผู้ช่วยเขียนโค้ดที่เข้ามาทำงานในโปรเจกต์ `Lab Stroke Multi-Window`

## บทบาทของ Agent

Agent ต้องช่วยพัฒนา pipeline สำหรับ patient-level stroke-risk prediction จากข้อมูล EHR โดยอิงแนวคิดจากงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

เป้าหมายของงานคือเปรียบเทียบ `single-shot baseline` กับ temporal feature models ที่สร้างจากหลายช่วงเวลาก่อน `reference date`

## หลักสำคัญของโปรเจกต์

- ใช้ข้อมูลระดับ patient เป็นหน่วยวิเคราะห์หลัก
- Stroke target ใช้ ICD-10 codes `I60-I68`
- Stroke patient ใช้ first stroke event เป็น `reference date`
- Non-stroke patient ใช้ last clinical visit เป็น `reference date`
- ห้ามใช้ records หลัง `reference date`
- Default temporal windows ตาม paper:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- Temporal feature extraction ต้องระวัง `data leakage`
- Metrics หลักคือ `sensitivity`, `specificity`, `G-Mean`

## โครงสร้างสำคัญ

```text
data/raw/            raw EHR data
docs/pipeline/       pipeline specification ราย stage
job/                 implementation notes และสรุปงานราย stage
output/              generated outputs จากการรัน pipeline
paper/               paper notes และ PDF reference
src/                 source code ของ pipeline
tests/               tests ถ้ามีหรือเพิ่มในอนาคต
README.md            ภาพรวมโปรเจกต์
WORKLOG.md           บันทึกงาน
agent.md             คู่มือ agent ไฟล์นี้
```

## Pipeline Stages

- `src/raw_data.py`: Stage 01 raw data audit
- `src/target_cohort.py`: Stage 02 target/cohort construction
- `src/data_cleaning.py`: Stage 03 data cleaning
- `src/eda.py`: Stage 04 exploratory data analysis
- `src/feature_engineering.py`: Stage 05 feature engineering
- `src/modeling.py`: Stage 06 modeling
- `src/feature_importance.py`: Stage 07 feature importance / ANOVA / PCA
- `src/validation.py`: Stage 08 validation
- `src/temporal_pipeline.py`: orchestrator ที่เรียกใช้ Stage 01-08 จาก modules แยก

## วิธีรัน Stage หลัก

ใช้ virtual environment ถ้ามี:

```powershell
.\.venv\Scripts\python.exe -m src.raw_data
.\.venv\Scripts\python.exe -m src.target_cohort
.\.venv\Scripts\python.exe -m src.data_cleaning
.\.venv\Scripts\python.exe -m src.eda
.\.venv\Scripts\python.exe -m src.feature_engineering
.\.venv\Scripts\python.exe -m src.modeling
.\.venv\Scripts\python.exe -m src.feature_importance
.\.venv\Scripts\python.exe -m src.validation
```

ถ้าไม่ได้ใช้ `.venv`:

```powershell
python -m src.raw_data
python -m src.target_cohort
python -m src.data_cleaning
python -m src.eda
python -m src.feature_engineering
python -m src.modeling
python -m src.feature_importance
python -m src.validation
```

รัน orchestrator รวม:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling
.\.venv\Scripts\python.exe -m src.temporal_pipeline
```

## Workflow สำหรับ Agent

1. อ่านเอกสาร stage ใน `docs/pipeline` ก่อนแก้โค้ด
2. อ่านไฟล์ source stage ก่อนหน้าที่เกี่ยวข้องใน `src`
3. เขียนหรือแก้โค้ดให้ตามรูปแบบเดิมของโปรเจกต์
4. สร้างหรืออัปเดต job note ใน `job` เมื่อ implement stage ใหม่
5. รัน stage ที่แก้เพื่อเช็คว่าโค้ดทำงานได้จริง
6. ถ้าแก้ pipeline รวม ให้รัน `src.temporal_pipeline --skip-modeling` อย่างน้อยหนึ่งครั้ง
7. สรุปผลรันและข้อจำกัดให้ผู้ใช้
8. ถ้าผู้ใช้สั่ง `commit/push` ให้ commit เฉพาะ code/docs ที่เกี่ยวข้อง

## Git และข้อมูลอ่อนไหว

อย่า commit/push สิ่งต่อไปนี้ เว้นแต่ผู้ใช้ยืนยันชัดเจนหลังแจ้งความเสี่ยง:

- `.venv/`
- `output/`
- generated patient-level CSV
- raw/derived medical data
- cache เช่น `__pycache__/`

ควร commit/push เฉพาะ:

- source code ใน `src/`
- documentation ใน `docs/`, `job/`, `paper/`
- `README.md`, `WORKLOG.md`, `agent.md`

## ข้อควรระวังเชิงงานวิจัย

- อย่าคำนวณ features จากข้อมูลหลัง stroke/reference date
- อย่า fit scaler/feature selector/PCA บนข้อมูลทั้งหมดก่อน cross-validation
- Feature selection และ PCA ต้อง fit เฉพาะ training fold
- Model comparison ควรใช้ patient-level paired predictions
- `G-Mean` เป็น metric หลัก เพราะ class imbalance สูง
- McNemar's test จะรันได้เมื่อมี paired predictions ของ baseline และ temporal model

## สถานะข้อมูลปัจจุบันที่ควรรู้

จากผลรันล่าสุดของ pipeline:

- raw patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13

ผลกระทบ:

- temporal model อาจ train ไม่ได้ เพราะ minority class ใน temporal-complete cohort น้อยเกินไป
- Stage 06/07/08 ต้องรองรับ `skipped` status พร้อมเหตุผล
- ควรพิจารณา sensitivity analysis เช่น window 90/180 วันในอนาคต โดยยังคง default paper windows เป็น baseline

## Style ของโค้ด

- ใช้ module แยกตาม stage
- ใช้ `dataclass` สำหรับ config
- เขียน output เป็นทั้ง `.csv`, `.json`, `.md` เมื่อเหมาะสม
- ใช้ `Path` จาก `pathlib`
- ใช้ `encoding="utf-8"` หรือ `utf-8-sig` สำหรับ CSV ที่ต้องเปิดใน Excel
- คอมเมนต์ภาษาไทยได้ โดยเน้นอธิบายเหตุผลของ logic ไม่ใช่อธิบายบรรทัดที่ชัดอยู่แล้ว

## Paper Reference

- Note: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- PDF: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- IEEE reference: `https://ieeexplore.ieee.org/abstract/document/11431866`
