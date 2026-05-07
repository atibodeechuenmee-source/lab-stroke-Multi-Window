# Worklog

## 2026-05-07

### Multi-Window Temporal Stroke-Risk Pipeline

- อ่าน paper และสร้าง note สรุปงานวิจัยที่ `paper/multi-window-temporal-features-stroke-risk-2026.md`
- สร้างเอกสาร pipeline ครบ Stage 00-09 ใน `docs/pipeline`
- สร้าง implementation notes ราย stage ใน `job`
- สร้าง `src/temporal_pipeline.py` เวอร์ชันแรกเป็น pipeline รวมจาก raw data ถึง feature/modeling scaffold
- สร้าง `README.md` และเอกสารสรุปภาพรวมโปรเจกต์

## 2026-05-08

### Stage Implementations

- Implement Stage 01 raw data audit: `src/raw_data.py`
- Implement Stage 02 target/cohort construction: `src/target_cohort.py`
- Implement Stage 03 data cleaning: `src/data_cleaning.py`
- Implement Stage 04 EDA: `src/eda.py`
- Implement Stage 05 feature engineering: `src/feature_engineering.py`
- Implement Stage 06 modeling: `src/modeling.py`
- Implement Stage 07 feature importance / ANOVA / PCA: `src/feature_importance.py`
- Implement Stage 08 validation: `src/validation.py`

### Documentation And Comments

- เพิ่มคอมเมนต์ภาษาไทยใน Stage 01-08 เพื่ออธิบาย flow, leakage guard, skip conditions และเหตุผลของ logic สำคัญ
- สร้าง `agent.md` เป็นคู่มือสำหรับ AI agent ที่เข้ามาทำงานในโปรเจกต์นี้
- อัปเดต README ให้สะท้อนสถานะล่าสุดของ stage modules และ orchestrator

### Temporal Pipeline Refactor

- Refactor `src/temporal_pipeline.py` จากไฟล์ที่มี logic ซ้ำ ให้เป็น orchestrator ที่เรียกใช้ stage modules แยกโดยตรง
- ทดสอบ orchestrator ด้วย:

```powershell
.\.venv\Scripts\python.exe -m src.temporal_pipeline --skip-modeling --output-dir output/pipeline_runs/orchestrator_test
```

ผลทดสอบ:

- Stage 01-05 รันสำเร็จ
- raw rows: 218,772
- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13
- Extract Set 1: 13 rows x 36 columns
- Extract Set 2: 13 rows x 266 columns
- Extract Set 3: 13 rows x 272 columns
- leakage audit passed: true

### Current Notes

- `.venv` ต้องมี `openpyxl` เพื่อให้ pandas อ่าน raw `.xlsx` ได้
- `output/` เป็น generated artifacts และไม่ควร commit/push โดยทั่วไป
- temporal-complete cohort ยังเล็กมาก จึงควรทำ sensitivity analysis เรื่อง window/completeness ในงานถัดไป
