# งาน: Implement Stage 06 Modeling

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/06-modeling.md` เพื่อ train และเปรียบเทียบโมเดล stroke-risk prediction โดยใช้ single-shot baseline เป็น comparator และใช้ Logistic Regression พร้อม `class_weight="balanced"` เป็น default ตาม paper

## ไฟล์โค้ดที่สร้าง

- `src/modeling.py`

## สิ่งที่โค้ดทำ

`src/modeling.py` เป็น CLI/module แยกสำหรับ Stage 06:

- โหลด feature tables จาก Stage 05:
  - `single_shot_features.csv`
  - `extract_set_1_features.csv`
  - `extract_set_2_features.csv`
  - `extract_set_3_features.csv`
- ใช้เฉพาะ numeric feature columns สำหรับ modeling
- train Logistic Regression พร้อม `class_weight="balanced"`
- ใช้ patient-level cross-validation:
  - ใช้ LOOCV สำหรับ feature table ขนาดเล็ก
  - ใช้ stratified patient-level CV สำหรับ table ขนาดใหญ่เพื่อให้รันได้จริง
- ตรวจว่า train/test patient ids ไม่ overlap ใน fold เดียวกัน
- เก็บ predicted probability, predicted class และ true label ต่อ patient
- คำนวณ metrics:
  - sensitivity
  - specificity
  - G-Mean
  - ROC-AUC
  - confusion matrix counts
- skip model อย่างโปร่งใสถ้า feature table มี class เดียวหรือ minority class น้อยเกินไป

## วิธีรัน

ใช้ค่า default:

```powershell
python -m src.modeling
```

ระบุ feature/output directory เอง:

```powershell
python -m src.modeling --feature-dir output/feature_engineering_output --output-dir output/model_output
```

ปรับจำนวน folds หรือ threshold:

```powershell
python -m src.modeling --max-folds 5 --threshold 0.5
```

## Output

Default output directory:

```text
output/model_output
```

ไฟล์ที่สร้าง:

- `model_cv_metrics.csv`
- `model_config_log.csv`
- `all_model_predictions.csv`
- `<model_name>_predictions.csv`
- `modeling_report.json`
- `modeling_report.md`

## Acceptance Criteria

- split เป็นระดับ patient ไม่ใช่ record
- ไม่มี patient เดียวกันอยู่ทั้ง train และ test ใน fold เดียวกัน
- baseline ใช้ single-shot features เท่านั้น
- temporal models ใช้ Extract Set 1/2/3 ตามนิยาม
- Logistic Regression ใช้ `class_weight="balanced"`
- predictions map กลับไปที่ patient id ได้

## สถานะ

Implemented แล้วเป็น module แยก สามารถใช้ output จาก `src.feature_engineering` ได้โดยตรง และ output พร้อมเป็น input ของ Stage 08 validation

## ผลการรันทดสอบล่าสุด

รันด้วย local `.venv` ที่ติดตั้ง `pandas` และ `scikit-learn` แล้ว:

```powershell
.\.venv\Scripts\python.exe -m src.modeling
```

ผลลัพธ์จาก feature tables ปัจจุบัน:

- `single_shot` completed ด้วย `StratifiedKFold_5`
- `single_shot` G-Mean = 0.9246, sensitivity = 0.9288, specificity = 0.9203, ROC-AUC = 0.9679
- `extract_set_1`, `extract_set_2`, `extract_set_3` ถูก skip เพราะ temporal-complete set มี positive class เพียง 1 ราย (`not_run_min_class_lt_2`)

ข้อสรุป: Stage 06 ทำงานได้ แต่ยังไม่สามารถเปรียบเทียบ temporal feature models ได้จริงจนกว่าจะปรับ completeness/window strategy ให้มี stroke cases มากพอใน temporal feature tables
