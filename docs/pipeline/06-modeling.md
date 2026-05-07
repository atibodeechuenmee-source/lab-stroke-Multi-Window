# Stage 06: Modeling

## Purpose

Train และ evaluate stroke-risk prediction models ให้ใกล้ paper มากที่สุด โดยใช้ Logistic Regression เป็น interpretable baseline และใช้ `class_weight="balanced"` เพื่อรับมือ class imbalance

## Input

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- Target column `stroke`

## Process

1. Load feature tables
2. Prepare numeric feature matrix
3. Keep patient-level independence
4. Select CV strategy:
   - Paper default: LOOCV
   - Project fallback: patient-level StratifiedKFold เมื่อข้อมูลใหญ่หรือเพื่อให้รันได้จริง
   - Skip เมื่อ class distribution ไม่พอ
5. Train Logistic Regression:

```text
LogisticRegression(class_weight="balanced")
```

6. Evaluate each model:
   - single-shot baseline
   - Extract Set 1
   - Extract Set 2
   - Extract Set 3
7. Save out-of-fold predictions
8. Rank models by G-Mean

## Output

- `model_cv_metrics.csv`
- `model_config_log.csv`
- `all_model_predictions.csv`
- `<model_name>_predictions.csv`
- `modeling_report.json`
- `modeling_report.md`

## Checks / Acceptance Criteria

- Single-shot baseline must always be attempted
- Must report skipped temporal models with reason
- Must prevent train/test patient overlap
- Must report sensitivity, specificity, G-Mean, ROC-AUC when possible
- Best model must be selected by G-Mean, not accuracy
- Must keep prediction files for Stage 08 McNemar testing

## Relation to Paper

Paper ใช้ Logistic Regression with `class_weight="balanced"` และ LOOCV เพราะข้อมูล imbalance และต้องการ patient-level independence Stage นี้จึงต้องรักษาแนวคิดเดียวกัน แม้โปรเจกต์จะมี fallback เพื่อให้รันได้จริงบนข้อมูลที่มีข้อจำกัด
