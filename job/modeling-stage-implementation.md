# งาน: Update Stage 06 Modeling

## เป้าหมาย

อัปเดต `src/modeling.py` ให้ทำ Stage 06 ตาม `docs/pipeline/06-modeling.md` ล่าสุด และสอดคล้องกับงานวิจัย `Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction`

Stage นี้ train/evaluate stroke-risk prediction model โดยใช้ `single-shot baseline` เป็น comparator เสมอ และใช้ Logistic Regression พร้อม `class_weight="balanced"` เป็น default ตาม paper

## ไฟล์โค้ดที่เกี่ยวข้อง

- `src/modeling.py`
- `docs/pipeline/06-modeling.md`

## สิ่งที่อัปเดตในโค้ด

เพิ่ม paper metadata:

- paper title
- method section: Classification Model
- algorithm: `LogisticRegression`
- class weight: `balanced`
- paper CV strategy: `LOOCV`
- primary selection metric: `G-Mean`

เพิ่ม metric:

- sensitivity
- specificity
- `G-Mean`
- ROC-AUC
- PR-AUC
- confusion matrix counts

เพิ่ม output/report ใหม่:

- `skipped_models_report.csv`
- `cv_policy_report.csv`
- `modeling_acceptance_checks.csv`

เพิ่ม model acceptance checks:

- single-shot baseline ถูก attempt เสมอ
- temporal models ที่ถูก skip ต้องมีเหตุผล
- ป้องกัน train/test patient overlap
- metrics สำคัญถูก report ครบ
- best model เลือกด้วย `G-Mean`
- prediction files พร้อมสำหรับ Stage 08 McNemar testing
- ใช้ `LogisticRegression(class_weight="balanced")`

เพิ่ม CV policy report:

- บอกว่า paper ใช้ `LOOCV`
- บอก actual CV strategy ของแต่ละ feature table
- ถ้าใช้ fallback หรือ skip ให้บันทึกเหตุผล

## Output จาก Stage 06

Default output directory:

```text
output/model_output
```

ไฟล์ที่ Stage 06 สร้าง:

- `model_cv_metrics.csv`
- `model_config_log.csv`
- `all_model_predictions.csv`
- `<model_name>_predictions.csv`
- `skipped_models_report.csv`
- `cv_policy_report.csv`
- `modeling_acceptance_checks.csv`
- `modeling_report.json`
- `modeling_report.md`

## Acceptance Checks

`modeling_acceptance_checks.csv` ตรวจหัวข้อหลักต่อไปนี้:

- single-shot baseline attempted
- skipped temporal models reported with reason
- train/test patient overlap prevented
- required metrics reported
- best model selected by `G-Mean`
- prediction files available for validation
- Logistic Regression balanced used

## วิธีรัน

ใช้ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.modeling
```

ระบุ feature/output directory เอง:

```powershell
.\.venv\Scripts\python.exe -m src.modeling --feature-dir output\pipeline_runs\stage05_paper_schema_test --output-dir output\pipeline_runs\stage06_update_test
```

ปรับจำนวน folds หรือ threshold:

```powershell
.\.venv\Scripts\python.exe -m src.modeling --max-folds 5 --threshold 0.5
```

## ผลทดสอบล่าสุด

ตรวจ syntax:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\modeling.py
```

ผลลัพธ์: ผ่าน

รัน Stage 06 ด้วย feature schema ที่ตรง paper จาก Stage 05:

```powershell
.\.venv\Scripts\python.exe -m src.modeling --feature-dir output\pipeline_runs\stage05_paper_schema_test --output-dir output\pipeline_runs\stage06_update_test
```

ผลลัพธ์สำคัญ:

- models seen: `single_shot`, `extract_set_1`, `extract_set_2`, `extract_set_3`
- models completed: 1
- models skipped: 3
- best model: `single_shot`
- best G-Mean: 0.9234
- acceptance checks: 7/7 ผ่าน

ผล single-shot:

- CV: `StratifiedKFold_5`
- patients: 13,635
- features: 21
- stroke cases: 969
- non-stroke cases: 12,666
- sensitivity: 0.9267
- specificity: 0.9202
- G-Mean: 0.9234
- ROC-AUC: 0.9683
- PR-AUC: 0.7501

ผล temporal models:

- `extract_set_1`: skipped, `not_run_min_class_lt_2`, patients 13, stroke 1, non-stroke 12
- `extract_set_2`: skipped, `not_run_min_class_lt_2`, patients 13, stroke 1, non-stroke 12
- `extract_set_3`: skipped, `not_run_min_class_lt_2`, patients 13, stroke 1, non-stroke 12

## ข้อควรระวัง

- Paper ใช้ `LOOCV` แต่ single-shot table ของโปรเจกต์มี 13,635 patients จึงใช้ fallback เป็น `StratifiedKFold_5` เพื่อให้รันได้จริง
- temporal feature tables ตอนนี้มี temporal-complete stroke เพียง 1 ราย จึงยัง train/evaluate temporal models ไม่ได้อย่างถูกต้อง
- การเปรียบเทียบ temporal vs single-shot ตาม paper จะทำจริงได้เมื่อ temporal-complete cohort มีทั้ง positive/negative classes เพียงพอ
- `output/` เป็น generated artifacts และอาจมี derived patient-level data จึงไม่ควร commit/push

## สถานะ

Implemented และทดสอบผ่านแล้ว
