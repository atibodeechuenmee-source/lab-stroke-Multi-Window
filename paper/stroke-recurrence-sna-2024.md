# Stroke Recurrence Prediction Using Machine Learning and Segmented Neural Network Risk Factor Aggregation

## ข้อมูลอ้างอิง

- ชื่อ paper: Stroke recurrence prediction using machine learning and segmented neural network risk factor aggregation
- ผู้แต่ง: Xueting Ding, Yang Meng, Liner Xiang และคณะ
- ปีที่เผยแพร่: 2024
- วันที่เผยแพร่: 2024-10-07
- วารสาร: Discover Public Health
- Volume/Article: 21, Article 119
- DOI: 10.1186/s12982-024-00199-6
- URL: https://doi.org/10.1186/s12982-024-00199-6

## ลิงก์อ้างอิง

- Paper: https://link.springer.com/article/10.1186/s12982-024-00199-6
- DOI: https://doi.org/10.1186/s12982-024-00199-6
- Code repository: https://github.com/yangmeng96/PilotSNA
- Data source: https://trinetx.com

## เหตุผลที่เลือก paper นี้

Paper นี้เกี่ยวข้องกับโปรเจกต์ของเราโดยตรง เพราะใช้ diagnosis data จาก EHR และใช้ ICD-10 เพื่อสร้าง risk factors สำหรับทำนาย stroke recurrence ภายในช่วงเวลาสั้น ๆ หลัง stroke event งานนี้ไม่ได้เน้นแค่เลือก classifier แต่เน้นขั้นตอน data aggregation จาก ICD code จำนวนมากให้กลายเป็น feature ระดับ risk factor ซึ่งเป็นปัญหาที่ใกล้กับ dataset ของเรา เพราะเรามี `PrincipleDiagnosis` และสามารถใช้รหัส ICD-10 สร้าง target หรือ feature เพิ่มเติมได้

อีกจุดที่น่าสนใจคือ paper นี้รายงานทั้ง ROC-AUC และ PR-AUC ซึ่งเหมาะกับงาน stroke ที่มักมี class imbalance และสอดคล้องกับ workflow ที่เราเริ่มใช้ PR-AUC ใน patient-level prediction แล้ว

## วัตถุประสงค์ของงานวิจัย

งานวิจัยนี้ต้องการพัฒนาแนวทางทำนาย stroke recurrence โดยแก้ปัญหาว่าข้อมูล diagnosis จาก EHR มี ICD-10 subcategory จำนวนมาก ทำให้การรวมข้อมูลแบบง่าย เช่น binary MAX อาจเสียข้อมูลเรื่องความซับซ้อนหรือ severity ของโรคร่วม

ผู้วิจัยเสนอวิธี Segmented Neural Network-Driven Aggregation หรือ SNA เพื่อรวม ICD subcategories เป็น feature ระดับ risk factor ก่อนนำไปเข้าโมเดล logistic regression และ random forest

## Dataset ที่ใช้

- แหล่งข้อมูล: TriNetX research network
- วันที่ดึงข้อมูล: 2023-10-23
- เครือข่ายข้อมูล: 55 Healthcare Organizations
- จำนวนผู้ป่วยใน network โดยรวม: ประมาณ 84 ล้านคน
- ขอบเขต pilot study: ผู้ป่วย 20,000 รายแรกที่มี diagnosis record ใด ๆ ในปี 2018
- Final cohort: 5,288 patients ที่มี stroke events ในปี 2018
- จำนวน stroke events: 22,804 events
- จำนวน stroke recurrence ภายใน 30 วัน: 13,062 events
- อายุเฉลี่ย: 65.14 ปี
- เพศหญิง: 52.44%
- กลุ่ม race/ethnicity หลัก: Non-Hispanic Whites 59.40%

## Target / Outcome

Target คือ stroke recurrence ภายใน 30 วันหลัง initial stroke diagnosis

นิยาม stroke event ใช้ ICD-10:

- `I60`
- `I61`
- `I63`
- `I64`
- `G45`

ในโมเดล outcome เป็น binary classification:

- `0` = ไม่มี recurrence
- `1` = มี recurrence ภายใน 30 วัน

## Features สำคัญ

กลุ่ม feature ที่ใช้ประกอบด้วย demographics และ risk factors จาก diagnosis history

Demographic features:

- อายุ
- เพศ
- race/ethnicity
- region
- marital status

Risk factors/comorbidities:

- obesity/overweight
- diabetes
- hypertension
- atrial fibrillation
- coronary and ischemic heart diseases
- hyperlipidemia
- nicotine exposure
- alcohol abuse/dependence
- history of TIA หรือ previous stroke

Risk factors เหล่านี้ถูกระบุจาก ICD-10 codes ภายใน 1 ปีก่อน stroke event ยกเว้น history of stroke ที่ตรวจย้อนหลังจาก record ก่อน event ปัจจุบัน

## Method / Model

Workflow หลัก:

1. แปลง longitudinal diagnosis data จาก long format เป็น wide format ตาม stroke event
2. แปลง ICD-10 subcategories เป็น binary columns
3. รวม subcategories ให้เป็น risk-factor-level features ด้วยหลายวิธี
4. เทียบ classifier คือ Logistic Regression และ Random Forest
5. ประเมินผลด้วย repeated train/test และ cross-validation

Aggregation methods ที่เปรียบเทียบ:

- `MAX`: ใช้ logical OR เพื่อตรวจว่ามี risk factor ใดเกิดขึ้นหรือไม่
- `SUM`: รวมจำนวน occurrence เพื่อสะท้อนความถี่หรือความเข้มข้นของ diagnosis
- `PCA`: ลดมิติแบบ linear
- `AE`: autoencoder แบบ unsupervised
- `SNA`: supervised segmented neural network-driven aggregation ที่ผู้วิจัยเสนอ

SNA เก็บแนวคิด encoder ของ autoencoder แต่ตัด decoder ออก แล้วใช้ label information เพื่อฝึกให้ latent representation แยก recurrence/non-recurrence ได้ดีขึ้น ข้อดีคือยังเก็บ feature ในระดับกลุ่ม risk factor ได้ ไม่กลายเป็น black-box feature ทั้งหมด

## Model Training และ Tuning

- ใช้ Logistic Regression และ Random Forest จาก scikit-learn
- แบ่งข้อมูล train/test เป็น 80/20
- ใช้ GridSearchCV สำหรับ hyperparameter tuning
- Random Forest tune พารามิเตอร์ เช่น `n_estimators`, `max_features`, `max_depth`, `min_samples_split`
- ใช้ fivefold cross-validation ในแต่ละรอบ
- ทำซ้ำทั้งหมด 5 repetitions เพื่อดูความเสถียรของผลลัพธ์

## Evaluation Metrics

Metrics ที่ใช้:

- Accuracy
- ROC-AUC
- PR-AUC

PR-AUC สำคัญมากในบริบท stroke recurrence เพราะช่วยสะท้อน precision และ recall ของ positive class ได้ดีกว่า accuracy เมื่อข้อมูลมี class imbalance หรือเมื่อ false negative มีผลทางคลินิกสูง

## ผลลัพธ์สำคัญ

ผลลัพธ์หลักคือ SNA ทำได้ดีที่สุดเมื่อเทียบกับ aggregation methods อื่น

เมื่อใช้ Logistic Regression:

- SNA ได้ accuracy เฉลี่ย 0.821
- ROC-AUC ประมาณ 0.902
- PR-AUC ประมาณ 0.910

เมื่อใช้ Random Forest:

- SNA ได้ accuracy เฉลี่ย 0.842
- ROC-AUC ประมาณ 0.928
- PR-AUC ประมาณ 0.940

ข้อสรุปของผู้วิจัยคือการปรับปรุง data representation/aggregation ก่อนเข้า classifier สามารถเพิ่ม performance ได้ชัดเจน โดยเฉพาะเมื่อข้อมูล diagnosis มี ICD subcategories จำนวนมาก

## ข้อจำกัดของงานวิจัย

- เป็น pilot study และใช้ subset ของข้อมูล ไม่ใช่ข้อมูลทั้งหมดใน TriNetX
- demographic variables ใน TriNetX มีจำกัด เช่น อายุ เพศ race/ethnicity และ region
- risk factors อิงจาก diagnosis records เท่านั้น อาจพลาดข้อมูลถ้าผู้ป่วยไปรักษานอก network หรือไม่มี diagnosis code ครบ
- ไม่มีข้อมูลพฤติกรรมบางอย่าง เช่น physical activity และ diet
- SNA ยังมีความเป็น black box เมื่อเทียบกับ logistic regression แบบตรง ๆ
- การนำไปใช้จริงอาจต้องมี visualization หรือ explainability tool เพื่อให้แพทย์เข้าใจเหตุผลของ prediction

## สิ่งที่นำมาใช้กับโปรเจกต์ของเราได้

- นำแนวคิด ICD-10 aggregation มาใช้สร้าง feature เพิ่มจาก diagnosis history ไม่ใช่ใช้ ICD-10 เฉพาะสร้าง target
- แยก risk factor groups จาก ICD-10 เช่น diabetes, hypertension, heart disease, kidney disease, dyslipidemia, previous stroke/TIA
- ทดลอง feature แบบ `MAX`, `COUNT`, `SUM` ก่อนใช้วิธีซับซ้อนกว่า เพราะอธิบายง่ายและเหมาะกับ production baseline
- สำหรับ patient-level 90-day prediction ของเรา ควรเพิ่ม feature ประวัติ stroke ก่อนหน้าและจำนวน diagnosis ในกลุ่มโรคสำคัญก่อน index date
- ควรใช้ PR-AUC ควบคู่ ROC-AUC ทุกครั้ง เพราะ target stroke ของเรามี positive class น้อย
- หากข้อมูลมีหลาย visit ต่อผู้ป่วย ควรสร้าง wide patient-event matrix ที่ตัดข้อมูลเฉพาะก่อน index date เพื่อลด data leakage
- Random Forest ยังเป็น baseline ที่เหมาะกับข้อมูล diagnosis aggregation เพราะรองรับ nonlinear interaction และ categorical/binary features ได้ดี

## หมายเหตุเพิ่มเติม

Paper นี้ช่วยย้ำว่าประสิทธิภาพของโมเดลไม่ได้ขึ้นกับ classifier เพียงอย่างเดียว แต่ขึ้นกับการออกแบบ feature representation อย่างมาก โดยเฉพาะในข้อมูล EHR ที่มีรหัส diagnosis จำนวนมากและมีความซ้ำซ้อนสูง
