# Worklog

## 2026-05-07

### Multi-Window Temporal Stroke-Risk Pipeline

- อ่าน `docs/pipeline/00-pipeline-overview.md` และใช้เป็น blueprint สำหรับโค้ด pipeline
- ตรวจ schema ตัวอย่างของ raw Excel `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- สร้าง `src/temporal_pipeline.py` สำหรับ pipeline หลัก:
  - raw data audit
  - cleaning
  - target/cohort construction
  - reference date assignment
  - post-reference leakage prevention
  - FIRST/MID/LAST window assignment
  - temporal completeness check
  - single-shot baseline features
  - Extract Set 1/2/3 temporal features
  - Logistic Regression validation พร้อม G-Mean และ McNemar's test
- สร้าง `src/__init__.py` เพื่อให้รันแบบ module ได้
- สร้าง job note ที่ `job/temporal-pipeline-implementation.md`

### Next Steps

- รัน pipeline แบบ `--skip-modeling` เพื่อตรวจ output cohort และ feature tables
- ตรวจจำนวน patients ที่ผ่าน temporal completeness criteria
- เพิ่ม module สำหรับ ANOVA F-test, PCA และ ANOVA+PCA ให้ครบตาม Stage 07
- เพิ่ม tests สำหรับ stroke ICD detection, reference date logic และ window assignment

