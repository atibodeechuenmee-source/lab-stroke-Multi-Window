# Assets Needed

รายการนี้ระบุไฟล์กราฟและตารางที่ต้องใช้ในการทำสไลด์จริง โดยใช้เฉพาะ output ของ EDA และ Feature Importance

## Slide-by-slide Assets

| Slide | Asset | Path | Role |
|---|---|---|---|
| 1 | Dataset metadata | `output/eda_output/column_types.csv` | ยืนยัน 218,772 rows และ 30 columns |
| 1 | Stroke target summary | `output/feature_importance_output/feature_importance_stroke_metrics.txt` | ยืนยัน stroke 5,170 records และ prevalence 2.36% |
| 1 | Dataset date range | `DATASET.md` | ยืนยันช่วงวันที่ 2014-10-01 ถึง 2024-06-30 |
| 2 | Column metadata | `output/eda_output/column_types.csv` | จัดกลุ่ม feature groups |
| 3 | Missing value chart | `output/eda_output/missing_values_percent.png` | กราฟหลักสำหรับ missingness |
| 3 | Missing value table | `output/eda_output/missing_summary.csv` | แหล่งตัวเลข FBS 74.14%, Triglyceride 71.99%, LDL 70.93%, TC:HDL_ratio 70.87% |
| 3 | Optional missing heatmap | `output/eda_output/missing_values_heatmap.png` | ใช้เป็น backup หากต้องการแสดง pattern missingness |
| 4 | Distribution overview | `output/eda_output/feature_distributions.png` | กราฟ distribution หลัก |
| 4 | Additional distributions | `output/eda_output/feature_distributions_2.png` | กราฟ distribution เสริม |
| 4 | Numeric summary | `output/eda_output/numeric_summary.csv` | แหล่งตัวเลข age, BMI, BPS, hypertension และ diabetes |
| 5 | Correlation heatmap | `output/eda_output/correlation_matrix.png` | กราฟหลักสำหรับ correlation |
| 5 | Ranked correlations | `output/eda_output/correlation_pairs_ranked.csv` | แหล่งตัวเลข LDL-Cholesterol, BW-BMI, eGFR-Creatinine |
| 5 | LDL boxplot | `output/eda_output/boxplot_LDL.png` | ใช้ประกอบ caveat เรื่อง LDL min = -30 |
| 5 | Numeric summary | `output/eda_output/numeric_summary.csv` | ยืนยัน LDL minimum |
| 6 | Pipeline source | `src/feature_importance.py` | ยืนยัน target, dropped fields, median imputation และ missing indicators |
| 6 | Pipeline notes | `job/feature-importance-stroke.md` | อ้างอิงคำอธิบาย leakage และ feature pipeline |
| 7 | Holdout metrics | `output/feature_importance_output/model_holdout_metrics.csv` | แหล่งตัวเลข ROC-AUC, F1, precision และ recall |
| 7 | Model comparison chart | `output/feature_importance_output/feature_importance_model_comparison.png` | ใช้ประกอบการเปรียบเทียบ model |
| 8 | RF importance chart | `output/feature_importance_output/feature_importance_stroke.png` | กราฟหลักของสไลด์ |
| 8 | RF importance table | `output/feature_importance_output/feature_importance_stroke.csv` | แหล่งตัวเลข hypertension 0.254, age 0.075, BMI 0.062 |
| 9 | SHAP bar chart | `output/feature_importance_output/shap_bar_random_forest.png` | กราฟหลักของสไลด์ |
| 9 | SHAP summary chart | `output/feature_importance_output/shap_summary_random_forest.png` | ใช้แทนหรือประกอบ SHAP bar หากต้องการ distribution |
| 9 | SHAP importance table | `output/feature_importance_output/shap_importance_random_forest.csv` | แหล่งตัวเลข hypertension 0.163, diabetes 0.050, Antihypertensive_flag 0.049, age 0.044 |
| 10 | Summary inputs | `output/eda_output/*`, `output/feature_importance_output/*` | ใช้สรุป insight และ caveat |

## Assets ที่ไม่ควรใช้ในเด็คนี้

- `output/model_output/*` เพราะเป็น output คนละขอบเขตกับเด็คนี้
- ไฟล์เอกสารหรือกราฟที่ไม่ได้มาจาก `output/eda_output/` หรือ `output/feature_importance_output/`
- ไฟล์ที่เน้นขั้นตอนอื่นนอกเหนือจาก EDA และ feature importance
