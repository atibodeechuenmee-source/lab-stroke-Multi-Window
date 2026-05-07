# งาน: Implement Stage 08 Validation

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/08-validation.md` เพื่อทำ validation layer ของโมเดล stroke prediction โดยเน้นข้อมูล imbalanced และใช้ `G-Mean` เป็น metric หลัก พร้อม baseline comparison, McNemar's test, leakage audit และ cohort attrition review

## ไฟล์โค้ดที่สร้าง

- `src/validation.py`

## สิ่งที่โค้ดทำ

`src/validation.py` เป็นโมดูล/CLI ของ Stage 08 โดยทำงานดังนี้:

- โหลด prediction files จาก Stage 06 (`output/model_output/*_predictions.csv`)
- คำนวณ metrics ต่อโมเดล:
  - `sensitivity`
  - `specificity`
  - `G-Mean`
  - `ROC-AUC` (ถ้ามี probability)
  - `PR-AUC` (ถ้ามี probability)
- สร้าง confusion matrix table ต่อโมเดล
- แยก baseline (`single_shot`) vs temporal models ในตาราง comparison
- เลือก best temporal model ตาม `G-Mean` (เมื่อมี)
- รัน McNemar's test แบบ paired prediction baseline vs best temporal (เมื่อมี prediction ของทั้งคู่)
- ดึง leakage evidence จาก Stage 04 (`output/eda_output/leakage_audit_summary.csv`)
- ดึง cohort attrition จาก Stage 02 (`output/target_cohort_output/cohort_attrition_report.csv`)
- สร้างรายงานสรุป `.json` และ `.md`

## Formula ที่ใช้

```text
G-Mean = sqrt(Sensitivity * Specificity)
```

McNemar's test (continuity-corrected):

```text
chi-square = (|b - c| - 1)^2 / (b + c)
```

โดย `b` = baseline ถูก challenger ผิด, `c` = baseline ผิด challenger ถูก

## Leakage Guard ที่ implement

- Validation ใช้ผล prediction จาก Stage 06/07 ที่ทำ patient-level CV อยู่แล้ว
- ตรวจซ้ำจาก Stage 04 ว่าไม่มี post-reference records (`no_post_reference_records`)
- ระบุสถานะการมีอยู่ของ Stage 07 summary เพื่อยืนยันเส้นทาง feature selection/PCA evidence

## วิธีรัน

ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.validation
```

ระบุ path เอง:

```powershell
.\.venv\Scripts\python.exe -m src.validation --model-dir output/model_output --feature-importance-dir output/feature_importance_output --cohort-dir output/target_cohort_output --eda-dir output/eda_output --output-dir output/validation_output
```

## Output

โฟลเดอร์ default:

```text
output/validation_output
```

ไฟล์ที่สร้าง:

- `validation_metrics.csv`
- `validation_confusion_matrices.csv`
- `roc_pr_auc_table.csv`
- `baseline_vs_temporal_comparison.csv`
- `mcnemar_test_report.csv`
- `leakage_audit_report.csv`
- `cohort_attrition_validation_view.csv`
- `validation_summary.json`
- `validation_report.md`

## ผลการรันล่าสุด

รันด้วย:

```powershell
.\.venv\Scripts\python.exe -m src.validation
```

ผลสรุป:

- `models_evaluated`: 1
- `baseline_model`: `single_shot`
- `best_model`: `single_shot`
- `best_g_mean`: `0.9245555768725037`
- `temporal_model_count`: 0
- `mcnemar_status`: `skipped`
- `mcnemar_reason`: `baseline_or_temporal_predictions_missing`
- `leakage_audit_passed`: `true`

สรุปเชิงงานวิจัย: โค้ด Stage 08 พร้อมสำหรับ baseline-vs-temporal significance testing แล้ว แต่ข้อมูลรอบนี้ยังไม่มี temporal predictions ที่ train สำเร็จ จึงยังไม่สามารถรัน McNemar comparison ตาม paper ได้

## Acceptance Criteria

- มี sensitivity/specificity/G-Mean ต่อโมเดลครบ
- baseline แยกจาก temporal models ชัดเจน
- มี McNemar report (completed หรือ skipped พร้อมเหตุผล)
- มี leakage audit report และ cohort attrition validation view
- ระบุ best model โดย `G-Mean` ไม่ใช่ accuracy

## สถานะ

Implemented แล้วใน `src/validation.py` และรันสร้าง artifacts สำเร็จ
