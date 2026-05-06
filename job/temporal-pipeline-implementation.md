# งาน: Implement Multi-Window Temporal Stroke-Risk Pipeline

## เป้าหมาย

สร้างโค้ด pipeline จาก `docs/pipeline/00-pipeline-overview.md` เพื่อแปลง raw EHR records เป็น patient-level feature tables สำหรับเปรียบเทียบ single-shot baseline กับ temporal feature models ตาม paper `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

## ไฟล์โค้ดที่สร้าง

- `src/__init__.py`
- `src/temporal_pipeline.py`

## สิ่งที่โค้ดทำ

โค้ดใน `src/temporal_pipeline.py` ครอบคลุมขั้นตอนหลักตาม overview:

- โหลด raw EHR data จาก Excel หรือ CSV
- สร้าง raw data audit เช่น schema, missingness และ column examples
- ทำ data cleaning เบื้องต้น เช่น date parsing, duplicate removal, numeric coercion, implausible value handling และ binary flag normalization
- สร้าง patient-level target/cohort จาก ICD-10 `I60-I68`
- กำหนด `reference date`
  - stroke patient ใช้ first stroke event
  - non-stroke patient ใช้ last visit
- ลบ post-reference records เพื่อกัน data leakage
- assign temporal windows:
  - FIRST: 21-9 เดือนก่อน reference date
  - MID: 18-6 เดือนก่อน reference date
  - LAST: 15-3 เดือนก่อน reference date
- ตรวจ temporal completeness
- สร้าง single-shot baseline จาก latest pre-reference record
- สร้าง Extract Set 1/2/3 สำหรับ temporal features
- train Logistic Regression พร้อม `class_weight="balanced"` ถ้าไม่สั่ง `--skip-modeling`
- ประเมิน sensitivity, specificity, G-Mean, ROC-AUC และ McNemar's test

## วิธีรัน

รันเฉพาะ audit/cohort/features:

```powershell
python -m src.temporal_pipeline --skip-modeling
```

รันรวม modeling:

```powershell
python -m src.temporal_pipeline
```

ระบุ raw path และ output directory เอง:

```powershell
python -m src.temporal_pipeline --raw-path data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx --output-dir output/pipeline_runs/temporal_pipeline
```

## Output หลัก

Default output อยู่ที่:

```text
output/pipeline_runs/temporal_pipeline
```

ไฟล์สำคัญ:

- `raw_data_output/raw_schema_summary.csv`
- `target_cohort_output/patient_level_cohort.csv`
- `target_cohort_output/pre_reference_records_with_windows.csv`
- `feature_engineering_output/single_shot.csv`
- `feature_engineering_output/extract_set_1.csv`
- `feature_engineering_output/extract_set_2.csv`
- `feature_engineering_output/extract_set_3.csv`
- `validation_output/validation_metrics.csv`
- `pipeline_manifest.json`

## ข้อควรระวัง

- โค้ดนี้ใช้ temporal windows ตาม paper เป็น default แต่ถ้า dataset จริงมี coverage ไม่พอ ควรทดลอง alternative windows เช่น 90/180 วัน
- Completeness criteria เข้มมาก เพราะต้องมี visit และ core numeric variables ครบในทุก window
- Feature selection/PCA stage ยังไม่ได้แยกเป็น module เต็มรูปแบบในรอบนี้ แต่โครง validation และ feature tables พร้อมให้ต่อยอด
- Modeling ใช้ stratified patient-level CV เป็น default ในโค้ดเพื่อให้รันได้จริงเร็วกว่า LOOCV

## สถานะ

Implemented เป็นโค้ด pipeline เบื้องต้นที่รันได้ต่อจาก raw Excel ของโปรเจกต์ และสอดคล้องกับ overview หลักเรื่อง patient-level cohort, reference date, leakage prevention, temporal windows, single-shot baseline และ Extract Set 1/2/3

