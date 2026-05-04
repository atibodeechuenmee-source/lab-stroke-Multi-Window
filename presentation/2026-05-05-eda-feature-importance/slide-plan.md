# Slide Plan: EDA และ Feature Importance

เด็คนี้มี 10 สไลด์เท่านั้น ใช้ภาษาไทยเป็นหลัก และวาง narrative จาก "ข้อมูลพร้อมวิเคราะห์แต่มีข้อจำกัด" ไปสู่ "feature importance ให้ insight ได้แต่ไม่ใช่ causal effect"

## Slide 1: Dataset พร้อมวิเคราะห์ แต่ stroke เป็น minority class

**Key message:** Dataset มีขนาดใหญ่และช่วงเวลายาวพอสำหรับการวิเคราะห์ แต่ stroke records มีเพียง 2.36% จึงต้องตีความผลโมเดลในบริบทของ class imbalance

**Visual asset:** KPI cards 4 ช่อง: 218,772 records, 30 columns, 2014-10-01 ถึง 2024-06-30, stroke 5,170 records หรือ 2.36%

**Source file:** `DATASET.md`, `output/eda_output/column_types.csv`, `output/feature_importance_output/feature_importance_stroke_metrics.txt`

**Speaker goal:** เปิดเรื่องให้ผู้ฟังเห็น scale ของข้อมูลและข้อจำกัดสำคัญตั้งแต่ต้นว่า positive class มีน้อยมาก

## Slide 2: Feature groups ครอบคลุมข้อมูลคลินิกหลายมิติ

**Key message:** ตัวแปรครอบคลุมหลายมิติ ตั้งแต่ demographic, body metrics, blood pressure, lab, kidney function, comorbidity และ medication flags

**Visual asset:** Grouped feature map แบ่งเป็น 7 กลุ่ม พร้อมตัวอย่างตัวแปร: age/sex, height/bw/bmi, bps/bpd, HDL/LDL/Triglyceride/Cholesterol/FBS/TC:HDL_ratio, eGFR/Creatinine, hypertension/diabetes/heart_disease/AF, Statin/Gemfibrozil/Antihypertensive_flag

**Source file:** `output/eda_output/column_types.csv`, `job/EDA-stroke.md`

**Speaker goal:** ทำให้ผู้ฟังเข้าใจว่า feature set ไม่ได้พึ่งตัวแปรชนิดเดียว แต่มีทั้ง clinical measurement และ derived flags

## Slide 3: Missing values สูงมากใน lab variables

**Key message:** Lab variables หลายตัวมี missingness มากกว่า 70% เช่น FBS 74.14%, Triglyceride 71.99%, LDL 70.93% และ TC:HDL_ratio 70.87%

**Visual asset:** `missing_values_percent.png` เป็นกราฟหลัก และใช้ `missing_summary.csv` เป็น source สำหรับ callout ตัวเลข

**Source file:** `output/eda_output/missing_summary.csv`, `output/eda_output/missing_values_percent.png`

**Speaker goal:** เน้นว่าข้อมูลแล็บไม่ได้ missing แบบเล็กน้อย และ missingness เองอาจสะท้อน workflow การตรวจหรือ risk profile ของผู้ป่วย

## Slide 4: ข้อมูลพื้นฐานชี้ population ที่มีความเสี่ยงสูง

**Key message:** ค่าเฉลี่ย age 62.78, BMI 24.91, BPS 134.50 และ prevalence ของ hypertension 71.15%, diabetes 30.97% บ่งชี้ว่าประชากรในข้อมูลมี risk burden สูง

**Visual asset:** KPI/stat cards คู่กับ `feature_distributions.png` หรือ `feature_distributions_2.png`

**Source file:** `output/eda_output/numeric_summary.csv`, `output/eda_output/feature_distributions.png`, `output/eda_output/feature_distributions_2.png`

**Speaker goal:** เชื่อมบริบททางคลินิกก่อนเข้า correlation และ modeling ว่าข้อมูลนี้เป็นกลุ่มที่มีโรคร่วมจำนวนมาก

## Slide 5: Correlation และ outlier บอกข้อควรระวังก่อน modeling

**Key message:** Correlation สูงในบางคู่ตัวแปร เช่น LDL-Cholesterol r=0.916, BW-BMI r=0.883, eGFR-Creatinine r=-0.768 และ LDL มีค่าต่ำสุด -30 ที่ต้องตรวจสอบคุณภาพข้อมูล

**Visual asset:** `correlation_matrix.png` พร้อม callout top correlation pairs และ outlier note จาก numeric summary

**Source file:** `output/eda_output/correlation_pairs_ranked.csv`, `output/eda_output/correlation_matrix.png`, `output/eda_output/numeric_summary.csv`, `output/eda_output/boxplot_LDL.png`

**Speaker goal:** อธิบายว่าก่อน modeling ต้องระวัง multicollinearity, redundant information และ data quality issue โดยเฉพาะค่าที่ผิดธรรมชาติ

## Slide 6: Feature importance pipeline ลด leakage จาก diagnosis/text fields

**Key message:** Target สร้างจาก `PrincipleDiagnosis` ด้วย ICD-10 `I60-I69*` แต่ไม่ใช้ diagnosis/text fields เป็น feature และจัดการ missing values ด้วย median imputation พร้อม missing indicators

**Visual asset:** Pipeline diagram: raw data -> target from PrincipleDiagnosis -> remove diagnosis/text fields -> median imputation + missing indicators -> train/evaluate -> feature importance/SHAP

**Source file:** `src/feature_importance.py`, `job/feature-importance-stroke.md`, `output/feature_importance_output/feature_importance_stroke_metrics.txt`

**Speaker goal:** สร้างความมั่นใจว่าการตีความ feature importance ลด risk ของ leakage จากฟิลด์ diagnosis และข้อความ

## Slide 7: Random Forest เหมาะเป็นโมเดลหลักสำหรับ interpretation

**Key message:** Random Forest ให้ holdout ROC-AUC 0.963 และ F1 0.523 จึงเหมาะเป็นโมเดลหลักสำหรับ interpretation ขณะที่ XGBoost recall สูงกว่า 0.873 แต่ precision ต่ำ 0.119

**Visual asset:** ตารางเปรียบเทียบ holdout metrics หรือ `feature_importance_model_comparison.png`

**Source file:** `output/feature_importance_output/model_holdout_metrics.csv`, `output/feature_importance_output/model_cv_metrics_summary.csv`, `output/feature_importance_output/feature_importance_model_comparison.png`

**Speaker goal:** อธิบายเหตุผลเชิง performance ว่าทำไมเด็คจะใช้ Random Forest เป็นแกนหลักในการตีความ feature importance

## Slide 8: Hypertension เป็นตัวแปรสำคัญที่สุด

**Key message:** RF importance ชี้ว่า hypertension เป็น feature อันดับหนึ่งด้วย importance 0.254 ตามด้วย age 0.075 และ BMI 0.062

**Visual asset:** `feature_importance_stroke.png` เป็นกราฟหลัก พร้อม callout top 3

**Source file:** `output/feature_importance_output/feature_importance_stroke.csv`, `output/feature_importance_output/feature_importance_stroke.png`

**Speaker goal:** ให้ผู้ฟังเห็นว่า signal หลักไม่ได้มาจาก lab เพียงอย่างเดียว แต่มี comorbidity และ clinical profile เป็นตัวขับเคลื่อนสำคัญ

## Slide 9: SHAP ยืนยันสัญญาณหลักของ hypertension, diabetes, age และ medication flags

**Key message:** SHAP ranking สนับสนุน RF importance โดย hypertension มี mean absolute SHAP 0.163 ตามด้วย diabetes 0.050, Antihypertensive_flag 0.049 และ age 0.044

**Visual asset:** `shap_bar_random_forest.png` เป็นกราฟหลัก หรือใช้ `shap_summary_random_forest.png` ถ้าต้องการแสดง distribution ของผลกระทบ

**Source file:** `output/feature_importance_output/shap_importance_random_forest.csv`, `output/feature_importance_output/shap_bar_random_forest.png`, `output/feature_importance_output/shap_summary_random_forest.png`

**Speaker goal:** ยืนยันว่า feature importance จากโมเดลและ SHAP ให้ภาพใกล้เคียงกัน แต่ยังต้องพูดว่าเป็น association ไม่ใช่ causal effect

## Slide 10: ข้อสรุปและข้อควรระวัง

**Key message:** Insight จาก EDA และ feature importance ใช้ชี้ทิศทางได้ แต่ต้องระวัง missingness, class imbalance, leakage และการตีความแบบ causal; next step คือ permutation importance, temporal validation และ patient-level dataset

**Visual asset:** Summary slide แบบ 2 columns: "What we learned" และ "What to validate next"

**Source file:** `output/eda_output/*`, `output/feature_importance_output/*`, `job/feature-importance-stroke.md`

**Speaker goal:** ปิดด้วยข้อสรุปที่นำไปใช้ต่อได้ และวาง guardrail ชัดเจนว่า feature importance ไม่ได้พิสูจน์เหตุและผล
