# Feature Importance for Stroke

เอกสารนี้อธิบายการทำ feature importance สำหรับ dataset ผู้ป่วยในโปรเจกต์นี้ โดยใช้สคริปต์ `code/feature_importance.py`

## วัตถุประสงค์

งานนี้ทำเพื่อดูว่าตัวแปรใดมีความสำคัญต่อการจำแนก record ที่เกี่ยวข้องกับ stroke มากที่สุด เพื่อใช้เป็นแนวทางสำหรับงานวิเคราะห์หรือ machine learning ขั้นต่อไป

## Target ที่ใช้

สร้าง target ชื่อ `stroke_flag` จากคอลัมน์วินิจฉัยหลัก:

- `PrincipleDiagnosis`

ถ้า `PrincipleDiagnosis` อยู่ในช่วง ICD-10 กลุ่ม `I60-I69*` จะกำหนดเป็น stroke record โดยครอบคลุมรหัสที่บันทึกแบบไม่มีจุด เช่น `I699`:

- `I60` subarachnoid hemorrhage
- `I61` intracerebral hemorrhage
- `I62` other nontraumatic intracranial hemorrhages
- `I63` cerebral infarction
- `I64` stroke, not specified as hemorrhage or infarction
- `I65-I69` cerebrovascular disease related codes, including sequelae codes such as `I69*`

ผลจาก dataset ปัจจุบัน:

- จำนวน records ทั้งหมด: 218,772
- stroke records: 5,170
- non-stroke records: 213,602
- stroke prevalence: 2.36%

## Features ที่ใช้

ใช้ feature เชิงโครงสร้างและตัวเลขจาก dataset เช่น:

- demographic: `sex`, `age`
- body measurements: `height`, `bw`, `bmi`
- lifestyle: `smoke`, `drinking`
- blood pressure: `bps`, `bpd`
- labs: `HDL`, `LDL`, `Triglyceride`, `Cholesterol`, `FBS`, `eGFR`, `Creatinine`, `TC:HDL_ratio`
- comorbidity flags: `AF`, `heart_disease`, `hypertension`, `diabetes`
- medication flags: `Statin`, `Gemfibrozil`, `Antihypertensive_flag`
- date features: `visit_year`, `visit_month`

ไม่ได้ใช้คอลัมน์ diagnosis หรือ text fields เป็น feature เพราะ `PrincipleDiagnosis` ถูกใช้สร้าง target และอาจทำให้เกิด data leakage

## Model ที่ใช้

ใช้และเปรียบเทียบโมเดล 2 แบบ:

- `RandomForestClassifier` จาก scikit-learn
- `XGBClassifier` จาก XGBoost

RandomForest ตั้งค่าหลัก:

- `n_estimators=200`
- `class_weight="balanced_subsample"`
- `min_samples_leaf=5`
- `min_samples_split=10`
- `max_features="sqrt"`
- `random_state=42`

การลด `min_samples_leaf` จากค่าเดิมช่วยลด over-smoothing และทำให้โมเดลจับ pattern ของกลุ่ม stroke ซึ่งเป็น minority class ได้มากขึ้น

XGBoost ตั้งค่าหลัก:

- `n_estimators=250`
- `max_depth=4`
- `learning_rate=0.04`
- `subsample=0.85`
- `colsample_bytree=0.85`
- `scale_pos_weight` คำนวณจากสัดส่วน non-stroke ต่อ stroke

ใช้ `SimpleImputer(strategy="median", add_indicator=True)` เพื่อจัดการ missing values และเพิ่ม missing indicator ให้โมเดลเห็นว่าค่าใดหายไป

แบ่งข้อมูล train/test ด้วยอัตรา 75/25 และใช้ stratified split เพื่อรักษาสัดส่วน stroke/non-stroke

เพิ่ม Stratified K-Fold Cross Validation จำนวน 3 folds โดยใช้ stratified sample สูงสุด 60,000 records เพื่อให้รองรับ dataset ขนาดใหญ่และลดเวลาในการรัน

## Output ที่ได้

ไฟล์ผลลัพธ์ถูกบันทึกในโฟลเดอร์ `output/feature_importance_output`:

- `output/feature_importance_output/feature_importance_stroke.csv` - ตาราง feature importance
- `output/feature_importance_output/feature_importance_stroke.png` - กราฟ top 20 feature importance
- `output/feature_importance_output/feature_importance_stroke_metrics.txt` - metrics ของโมเดล
- `output/feature_importance_output/model_cv_metrics.csv` - metrics ราย fold จาก Stratified K-Fold CV
- `output/feature_importance_output/model_cv_metrics_summary.csv` - ค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของ CV metrics
- `output/feature_importance_output/model_holdout_metrics.csv` - metrics เปรียบเทียบโมเดลบน holdout test set
- `output/feature_importance_output/feature_importance_model_comparison.csv` - ตารางเปรียบเทียบ feature importance ระหว่างโมเดล
- `output/feature_importance_output/feature_importance_model_comparison.png` - กราฟเปรียบเทียบ feature importance ระหว่างโมเดล
- `output/feature_importance_output/shap_summary_random_forest.png` - SHAP summary plot
- `output/feature_importance_output/shap_bar_random_forest.png` - SHAP mean absolute importance
- `output/feature_importance_output/shap_local_positive_random_forest.png` - local SHAP ของตัวอย่าง stroke
- `output/feature_importance_output/shap_local_negative_random_forest.png` - local SHAP ของตัวอย่าง non-stroke
- `output/feature_importance_output/shap_importance_random_forest.csv` - ตาราง SHAP importance

## ผลลัพธ์ของโมเดล

ผลจาก holdout test set:

| Model | ROC-AUC | Accuracy | Precision | Recall | F1-score |
|---|---:|---:|---:|---:|---:|
| RandomForest | 0.9630 | 0.9715 | 0.4329 | 0.6589 | 0.5225 |
| XGBoost | 0.9357 | 0.8443 | 0.1191 | 0.8732 | 0.2096 |

ผลจาก Stratified K-Fold CV:

| Model | ROC-AUC mean | ROC-AUC std | Precision mean | Recall mean | F1 mean |
|---|---:|---:|---:|---:|---:|
| RandomForest | 0.9365 | 0.0033 | 0.3723 | 0.4545 | 0.4093 |
| XGBoost | 0.9288 | 0.0060 | 0.1298 | 0.8299 | 0.2245 |

เนื่องจาก stroke class มีสัดส่วนเพียง 2.36% ควรตีความ precision, recall และ AUC ในบริบทของ class imbalance

ในผลรอบนี้ RandomForest มี ROC-AUC และ F1-score สูงกว่า ส่วน XGBoost มี recall สูงกว่าแต่ precision ต่ำกว่า จึงเหมาะกับโจทย์ที่ต้องการจับผู้ป่วย stroke ให้ได้มากขึ้นและยอมรับ false positive ได้มากขึ้น

## Top Features

Top 20 features จาก Random Forest impurity-based importance:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `hypertension` | 0.3050 |
| 2 | `age` | 0.0690 |
| 3 | `Antihypertensive_flag` | 0.0547 |
| 4 | `visit_year` | 0.0538 |
| 5 | `bmi` | 0.0532 |
| 6 | `diabetes` | 0.0501 |
| 7 | `bw` | 0.0427 |
| 8 | `height` | 0.0423 |
| 9 | `Statin` | 0.0394 |
| 10 | `bps` | 0.0383 |
| 11 | `bpd` | 0.0301 |
| 12 | `visit_month` | 0.0190 |
| 13 | `drinking` | 0.0173 |
| 14 | `LDL` | 0.0161 |
| 15 | `eGFR` | 0.0152 |
| 16 | `smoke` | 0.0144 |
| 17 | `Creatinine` | 0.0133 |
| 18 | `heart_disease` | 0.0128 |
| 19 | `missingindicator_HDL` | 0.0120 |
| 20 | `sex` | 0.0113 |

## ข้อสังเกต

- `hypertension` สำคัญสูงมาก ซึ่งสอดคล้องกับความเสี่ยง stroke และ paper ที่สรุปไว้ใน `paper/`
- `Antihypertensive_flag`, `bps`, `bpd` สะท้อนบทบาทของความดันและการรักษาความดัน
- `age`, `diabetes`, `bmi` เป็น risk factors ที่สอดคล้องกับความรู้ทางคลินิก
- missing indicators ของ lab บางตัวติด top features แปลว่า pattern การมี/ไม่มีผลแล็บเองอาจสัมพันธ์กับ target
- `visit_year` มีความสำคัญพอสมควร อาจสะท้อนแนวโน้มข้อมูลตามเวลา, policy, coding practice หรือ data collection pattern

## ข้อควรระวัง

- Feature importance แบบ impurity-based ของ Random Forest อาจ bias ไปทางตัวแปรต่อเนื่องหรือ feature ที่มี split ได้หลายแบบ
- ค่า importance ไม่ได้แปลว่าเป็น causal effect
- Target สร้างจาก `PrincipleDiagnosis` ใน record เดียวกัน จึงควรระวังเรื่อง temporal leakage หากนำไปทำนายอนาคตจริง
- Medication flags อาจเป็นสัญญาณหลังเกิดโรคหรือหลังแพทย์ประเมินความเสี่ยงแล้ว ควรตรวจ timeline ก่อนใช้ในโมเดล production

## งานที่ควรทำต่อ

- ทำ permutation importance เพิ่มเพื่อยืนยัน ranking
- สร้าง patient-level dataset แทน record-level dataset
- กำหนด prediction window ให้ชัด เช่น ทำนาย stroke ภายใน 1 ปีหรือ 3 ปี
- ใช้เฉพาะ feature ที่เกิดก่อน outcome เพื่อป้องกัน data leakage
- ทดลองโมเดลอื่น เช่น Logistic Regression, XGBoost หรือ Gradient Boosting
- ทำ SHAP analysis เพื่ออธิบายผลราย feature และรายผู้ป่วย
