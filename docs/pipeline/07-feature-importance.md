# Feature Importance

## Goal

อธิบายว่า features ใดมีอิทธิพลต่อโมเดล และตรวจความสอดคล้องของ importance ระหว่างโมเดลและวิธีอธิบายผล

## Inputs

- Trained model pipelines
- Feature names หลัง preprocessing
- Holdout/test data หรือ sample สำหรับ explanation
- Existing script/output: `src/feature_importance.py`, `output/feature_importance_output/`

## Steps

1. Export impurity-based importance สำหรับ RandomForest หรือ tree-based models
2. Export XGBoost importance ถ้ามี XGBoost model
3. เปรียบเทียบ top features ระหว่างโมเดล
4. สร้าง SHAP global summary และ SHAP bar plot
5. สร้าง local SHAP สำหรับตัวอย่าง positive และ negative
6. สรุป clinical interpretation และข้อจำกัด

## Outputs

- Feature importance CSV
- Feature importance plots
- Model comparison importance table/plot
- SHAP summary, bar, local explanation plots
- Interpretation notes

## Checks

- Importance ไม่ใช่ causal effect
- Impurity-based importance อาจ bias ต่อ continuous/high-cardinality features
- Missing indicators ที่สำคัญควรตีความเป็น pattern การมีหรือไม่มีข้อมูล ไม่ใช่ค่าทาง lab โดยตรง
- Local SHAP ควรระบุว่าเป็นตัวอย่างเฉพาะราย ไม่ใช่ข้อสรุปทั้ง cohort
