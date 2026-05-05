# คำถามที่อาจารย์น่าจะถาม: EDA และ Feature Importance

เอกสารนี้เตรียมไว้สำหรับตอบคำถามจากสไลด์ `2026-05-05-eda-feature-importance` และผล pipeline ล่าสุดของโปรเจกต์ stroke prediction

หมายเหตุสำคัญ: สไลด์ชุดเดิมมีบางส่วนที่อธิบาย feature importance แบบ record-level โดยใช้ `stroke_flag` จาก `PrincipleDiagnosis` แต่ workflow ล่าสุดของโปรเจกต์ถูกปรับให้ตรงกับโจทย์หลักแล้ว คือ patient-level prediction ว่า "คนไข้คนนี้จะเป็น stroke ภายในอนาคตไหม" โดยใช้ target `stroke_3m` หรือการเกิด stroke ภายใน 90 วันหลัง index date

## 1. โจทย์จริงของงานนี้คืออะไร

คำตอบ:

โจทย์หลักคือการทำนายระดับคนไข้ว่า คนไข้รายหนึ่งมีโอกาสเกิด stroke ภายในอนาคตหรือไม่ โดยใน pipeline ปัจจุบันกำหนด horizon เป็น 90 วัน และใช้ target ชื่อ `stroke_3m`

ดังนั้นหน่วยวิเคราะห์หลักไม่ใช่ "แถว visit" แต่เป็น "คนไข้" หนึ่งคนต่อหนึ่งแถวใน feature table สุดท้าย เหตุผลคือถ้าโจทย์ถามว่า "คนไข้คนนี้จะเป็น stroke ไหม" การนับแบบแถว visit อาจทำให้คนไข้คนเดียวมีหลาย record และเสี่ยงทำให้ train/test มีข้อมูลของคนเดียวกันปนกัน ซึ่งเป็น data leakage ได้

ในงานนี้ `stroke_flag` ยังมีประโยชน์ แต่ใช้เป็น event marker ระดับ record เพื่อหา event date จาก ICD-10 ไม่ใช่ target สุดท้ายของโมเดล

## 2. `stroke_flag` กับ `stroke_3m` ต่างกันอย่างไร

คำตอบ:

`stroke_flag` เป็นตัวบอกว่า record หรือ visit นั้นมี diagnosis หลักเข้ากลุ่ม stroke หรือไม่ โดยสร้างจาก `PrincipleDiagnosis` ที่เป็น ICD-10 ช่วง `I60-I69*`

ส่วน `stroke_3m` เป็น target ระดับคนไข้ ใช้ตอบว่า หลัง index date คนไข้เกิด stroke ภายใน 90 วันหรือไม่

พูดสั้น ๆ คือ:

- `stroke_flag` = event marker ระดับแถว
- `stroke_3m` = prediction target ระดับคนไข้

จุดนี้สำคัญมาก เพราะถ้าใช้ `stroke_flag` เป็น target สำหรับโจทย์อนาคต โมเดลอาจกลายเป็นการจำแนกว่า visit นั้นเป็น stroke visit หรือไม่ ไม่ใช่การทำนายล่วงหน้า

## 3. ทำไมต้องเปลี่ยนจาก record-level เป็น patient-level

คำตอบ:

เพราะโจทย์ถามระดับคนไข้ ไม่ได้ถามระดับ visit ถ้าใช้ record-level คนไข้หนึ่งคนอาจมีหลายแถว และอาจเกิดปัญหา 3 อย่าง

1. ข้อมูลของคนไข้เดียวกันอาจหลุดไปอยู่ทั้ง train และ test ทำให้ performance ดูดีเกินจริง
2. โมเดลอาจเรียนรู้ pattern ของ visit หลังเกิดโรค แทนที่จะเรียนรู้ความเสี่ยงก่อนเกิดโรค
3. การตีความผลจะตอบผิดหน่วย จาก "คนไข้เสี่ยงไหม" กลายเป็น "แถวนี้เป็น stroke record ไหม"

ดังนั้น pipeline ล่าสุดจึงสร้าง `data/processed/patient_level_90d_stroke.csv` ที่มี 13,031 คนไข้ และใช้ `stroke_3m` เป็น target หลัก

## 4. Dataset มีขนาดเท่าไร และ target imbalance แค่ไหน

คำตอบ:

ใน raw data มี 218,772 records และประมาณ 30-31 columns ครอบคลุมช่วงวันที่ 2014-10-01 ถึง 2024-06-30

ถ้ามองแบบ record-level มี stroke event marker 5,170 records หรือประมาณ 2.36%

แต่หลังแปลงเป็น patient-level สำหรับโจทย์ 90 วัน มี 13,031 คนไข้ โดยมี positive `stroke_3m` จำนวน 406 คน หรือ prevalence 3.12%

แปลว่า positive class มีน้อยมาก ต้องระวังการใช้ accuracy เพราะถ้าโมเดลทายว่า "ไม่ stroke" เกือบทั้งหมด ก็ยังได้ accuracy สูง แต่ไม่มีประโยชน์ในการจับ stroke class

## 5. ทำไมไม่ควรดู accuracy อย่างเดียว

คำตอบ:

เพราะ stroke positive class มีประมาณ 3.12% เท่านั้น ถ้าโมเดลทำนายทุกคนเป็น non-stroke จะได้ accuracy ประมาณ 96.88% ทันที แต่ recall ของ stroke จะเป็น 0

ตัวอย่างจาก holdout ล่าสุด RandomForest ได้ accuracy 0.9687 แต่ precision, recall และ F1 ของ stroke class เป็น 0 เพราะไม่ทาย positive เลย

ดังนั้น metric ที่ควรดูร่วมกันคือ PR-AUC, recall, precision, F1 และ confusion matrix โดยเฉพาะ recall ของ stroke class เพราะโจทย์เชิง screening มักไม่อยากพลาดคนที่มีความเสี่ยงสูง

## 6. EDA พบอะไรสำคัญที่สุด

คำตอบ:

EDA พบประเด็นสำคัญ 4 เรื่อง

1. ข้อมูลมีขนาดใหญ่และมีช่วงเวลายาวพอสำหรับการวิเคราะห์
2. positive class มีน้อยมาก ทำให้เป็น class imbalance problem
3. lab variables หลายตัวมี missing สูงมาก เช่น FBS 74.14%, Triglyceride 71.99%, LDL 70.93%, TC:HDL_ratio 70.87%, HDL 70.40%, Cholesterol 70.08%, eGFR 67.12%, Creatinine 64.84%
4. มี feature บางคู่สัมพันธ์กันสูง เช่น LDL-Cholesterol, BW-BMI, eGFR-Creatinine และมีค่าผิดธรรมชาติบางตัว เช่น LDL ติดลบ ซึ่งต้องผ่าน data cleaning

สรุปคือข้อมูลมีศักยภาพ แต่ต้องจัดการ missing, outlier, leakage และ class imbalance ก่อน modeling

## 7. Missing values สูงมาก แบบนี้ใช้ข้อมูล lab ได้ไหม

คำตอบ:

ใช้ได้ แต่ต้องระวังและอธิบายให้ชัดว่า missing ไม่ใช่แค่ noise เสมอไป ในข้อมูลโรงพยาบาล การที่ lab หายอาจแปลว่าไม่ได้ถูกส่งตรวจ ซึ่งอาจสัมพันธ์กับความเสี่ยงหรือ workflow การรักษา

ใน modeling จึงใช้ `SimpleImputer(strategy="median", add_indicator=True)` เพื่อทำ 2 อย่างพร้อมกัน

1. เติมค่าที่หายด้วย median เพื่อให้โมเดลรับข้อมูลได้
2. เพิ่ม missing indicator เพื่อให้โมเดลเรียนรู้ pattern ว่าค่านี้เคยหายหรือไม่

แต่ต้องตีความ missing indicator อย่างระวัง ถ้า missing indicator สำคัญ ไม่ได้แปลว่า "ค่า lab นั้นสูงหรือต่ำ" แต่แปลว่า "รูปแบบการมีหรือไม่มีผล lab" มี signal ต่อโมเดล

## 8. ทำไมใช้ median imputation

คำตอบ:

เพราะข้อมูล clinical และ lab มักมี outlier และ distribution เบ้ การใช้ mean อาจถูกดึงโดยค่าผิดปกติได้ง่ายกว่า median

median จึงเป็น baseline ที่ค่อนข้าง robust สำหรับข้อมูล numeric clinical tabular ในขั้นต้น และการใส่ imputer ไว้ใน sklearn pipeline ช่วยให้ imputer fit เฉพาะ train fold ไม่แอบใช้ข้อมูลจาก validation/test

## 9. มี data leakage อะไรที่ต้องระวัง

คำตอบ:

มีหลายจุด

จุดแรกคือ diagnosis fields เช่น `PrincipleDiagnosis` และ `ComorbidityDiagnosis` เพราะ `PrincipleDiagnosis` ใช้สร้าง stroke event marker ถ้านำกลับมาเป็น feature โมเดลจะเห็นคำตอบโดยตรง

จุดที่สองคือ text fields เช่น รายการยา หรือข้อมูลที่อาจเกิดหลัง outcome ถ้าไม่ตรวจ timeline ให้ดี อาจเป็นสัญญาณหลังเกิดโรค ไม่ใช่สัญญาณก่อนเกิดโรค

จุดที่สามคือ patient leakage ถ้าคนไข้คนเดียวกันอยู่ทั้ง train และ test โมเดลจะดูเหมือนเก่งเกินจริง

ใน pipeline ล่าสุดจึง exclude `hn`, `index_date`, `event_date`, `days_to_event`, `stroke_3m` ออกจาก feature และ split ที่ patient-level พร้อมตรวจว่า `hn` ไม่ overlap ระหว่าง train/test

## 10. ทำไม `index_year` และ `index_month` ติด feature importance สูง ต้องกังวลไหม

คำตอบ:

ต้องกังวลในเชิง temporal drift แต่ยังไม่สรุปว่า leakage ทันที

`index_year` และ `index_month` อาจสะท้อนหลายอย่าง เช่น แนวทางการ coding ที่เปลี่ยนตามเวลา, policy โรงพยาบาล, availability ของ lab, รูปแบบการมารับบริการ หรือ cohort construction

ใน leakage audit ล่าสุดจึง flag `index_year` และ `index_month` เป็น features requiring review เพราะถ้าจะเอาโมเดลไปใช้จริงในอนาคต โมเดลอาจพึ่งพา pattern ตามปีมากเกินไป และ performance อาจตกเมื่อ distribution เปลี่ยน

คำตอบที่ดีคือ เรายังเก็บไว้เพื่อ exploratory modeling แต่ก่อน production ควรทำ temporal validation และทดลอง model ที่ตัด calendar features ออกเพื่อเปรียบเทียบ

## 11. Feature importance บอกเหตุและผลได้ไหม

คำตอบ:

ไม่ได้ Feature importance บอกว่า feature นั้นช่วยให้โมเดลทำนายได้มากแค่ไหนในข้อมูลและโมเดลชุดนี้ แต่ไม่ได้พิสูจน์ว่า feature นั้นเป็นสาเหตุของ stroke

ตัวอย่างเช่น hypertension สำคัญต่อโมเดล ซึ่งสอดคล้องกับความรู้ทางคลินิก แต่จากงานนี้เพียงอย่างเดียวเราพูดได้ว่า hypertension เป็น predictive signal ไม่ใช่สรุป causal effect

โดยเฉพาะ feature อย่าง missing indicator หรือ medication flag ยิ่งต้องระวัง เพราะอาจสะท้อน workflow การรักษา ไม่ใช่ biological cause โดยตรง

## 12. ทำไมต้องใช้ SHAP เพิ่ม ทั้งที่มี feature importance แล้ว

คำตอบ:

feature importance แบบ tree-native เช่น impurity-based importance ให้ ranking เร็วและอ่านง่าย แต่มีข้อจำกัดคืออาจ bias ไปทาง feature ที่เป็น continuous หรือมี split ได้หลายแบบ

SHAP ใช้ดู contribution ของ feature ต่อ prediction ในเชิง model explanation มากขึ้น โดยดูทั้ง global importance และ local explanation รายคนไข้

ใน pipeline ล่าสุด SHAP ใช้กับโมเดลที่ดีที่สุดตาม PR-AUC คือ `xgboost` และสร้างทั้ง summary plot, bar plot และ local SHAP positive/negative case

อย่างไรก็ตาม SHAP ก็ยังเป็น explanation ของโมเดล ไม่ใช่ causal proof

## 13. ทำไมผลสไลด์เดิมบอก RandomForest ดี แต่ pipeline ล่าสุดเลือก XGBoost

คำตอบ:

สไลด์เดิมเป็นงาน feature importance แบบ record-level ที่ใช้ `stroke_flag` เป็น target เพื่อสำรวจเบื้องต้น ผลตอนนั้น RandomForest ดูดีกว่าใน F1 และ ROC-AUC

แต่ pipeline ล่าสุดแก้โจทย์เป็น patient-level prediction ด้วย target `stroke_3m` แล้ว ใน setting ล่าสุด XGBoost มี PR-AUC สูงที่สุดบน holdout จึงถูกเลือกเป็น best model

นี่ไม่ใช่ contradiction แต่เป็นคนละ task:

- เดิม: จำแนก stroke record จาก visit-level data
- ล่าสุด: ทำนาย stroke ภายใน 90 วันระดับคนไข้

ถ้าอาจารย์ถาม ให้ตอบว่าเราพบข้อจำกัดของสไลด์เดิมและแก้ pipeline ให้ตรงโจทย์แล้ว

## 14. ผลโมเดลล่าสุดเป็นอย่างไร

คำตอบ:

บน patient-level holdout set โมเดลที่ดีที่สุดตาม PR-AUC คือ XGBoost

ผล holdout:

- ROC-AUC = 0.8850
- PR-AUC = 0.2172
- Accuracy = 0.8567
- Precision = 0.1470
- Recall = 0.7451
- F1 = 0.2456

Confusion matrix ที่ threshold 0.5 คือ `[[2715, 441], [26, 76]]`

แปลว่าใน holdout positive 102 คน โมเดลจับได้ 76 คน และพลาด 26 คน แต่มี false positive 441 คน จึงเหมาะกับการใช้เป็น screening/research signal มากกว่าการตัดสินใจทางคลินิกทันที

## 15. PR-AUC 0.2172 ต่ำไหม

คำตอบ:

ถ้าดูแบบทั่วไปอาจดูต่ำ แต่ต้องเทียบกับ baseline prevalence ก่อน เพราะ positive prevalence ใน holdout อยู่ประมาณ 3.13%

PR-AUC baseline ของ random model จะใกล้ prevalence คือประมาณ 0.031 ดังนั้น PR-AUC 0.2172 สูงกว่า baseline หลายเท่า แปลว่าโมเดลมี signal จริง

แต่ยังไม่สูงพอสำหรับ clinical decision-making โดยตรง เพราะ precision ที่ threshold 0.5 ยังอยู่ที่ 0.1470 หรือประมาณ 14.7%

## 16. Recall สูงแต่ precision ต่ำ แปลว่าอะไร

คำตอบ:

Recall 0.7451 แปลว่าโมเดลจับ stroke positive ได้ประมาณ 74.5% ของคนที่เป็น stroke ภายใน 90 วัน

Precision 0.1470 แปลว่าในกลุ่มที่โมเดลทำนายว่าเสี่ยง มีเพียงประมาณ 14.7% ที่เป็น positive จริง

ภาพรวมคือโมเดลค่อนข้าง sensitive แต่ false positive เยอะ เหมาะกว่าในบทบาท screening หรือ prioritization ที่ต้องการไม่พลาดผู้เสี่ยงสูง แต่ยังไม่เหมาะใช้เป็นคำตัดสินสุดท้าย

## 17. ถ้าอยากลด false positive ต้องทำอย่างไร

คำตอบ:

ต้องปรับ threshold ให้สูงขึ้น แต่ trade-off คือ recall จะลดลง

จาก threshold analysis ล่าสุด:

- threshold 0.5: precision 0.1470, recall 0.7451
- threshold 0.6: precision 0.1784, recall 0.6471
- threshold 0.7: precision 0.1975, recall 0.4608
- threshold 0.9: precision 0.5455, recall 0.0588

ถ้าต้องการลด false positive อาจเลือก threshold สูงขึ้น แต่ถ้าใช้เพื่อ screening stroke ซึ่งไม่อยากพลาดเคสจริงมากเกินไป threshold สูงเกินไปอาจไม่เหมาะ

## 18. ทำไม RandomForest ล่าสุด accuracy สูงแต่ recall เป็น 0

คำตอบ:

เพราะข้อมูล imbalance มาก RandomForest ที่ threshold default 0.5 เลือกทำนายทุกคนเป็น negative ทำให้ถูกกับ majority class จำนวนมาก จึงได้ accuracy 0.9687 แต่จับ positive ไม่ได้เลย

นี่เป็นตัวอย่างชัดเจนว่าทำไม accuracy ไม่พอ ต้องดู confusion matrix และ recall ของ stroke class

## 19. Calibration สำคัญอย่างไร

คำตอบ:

Calibration สำคัญถ้าจะตีความ predicted probability เป็นความเสี่ยงจริง เช่น ถ้าโมเดลบอก 20% เราต้องรู้ว่าในกลุ่มที่โมเดลให้ประมาณ 20% มี stroke จริงใกล้ 20% หรือไม่

ใน validation ล่าสุดมี Brier score 0.0927 และสร้าง calibration summary/curve แล้ว แต่ยังสรุปว่า predicted probabilities ต้องตรวจ calibration เพิ่มก่อนนำไปใช้เป็น absolute risk estimate

ดังนั้นตอนนี้ควรใช้ score เป็น relative risk ranking มากกว่าใช้เป็น probability ทางคลินิกโดยตรง

## 20. ทำไมต้องมี leakage audit

คำตอบ:

เพราะ feature importance และ performance จะเชื่อถือได้ก็ต่อเมื่อไม่มี feature ที่แอบเห็นคำตอบหรือข้อมูลหลัง outcome

Leakage audit ล่าสุดตรวจชื่อ feature และ forbidden columns พบว่ามี features ที่ต้อง review คือ `index_year` และ `index_month` เพราะเป็น calendar features ที่อาจสะท้อน temporal drift

ส่วน target/identifier เช่น `hn`, `event_date`, `days_to_event`, `stroke_3m` ไม่ได้ถูกใช้เป็น model features

## 21. Feature ที่สำคัญล่าสุดมีอะไรบ้าง

คำตอบ:

ใน patient-level feature importance ล่าสุด:

RandomForest top features ได้แก่ `index_year`, `history_days_observed`, `eGFR_missing_rate`, `age_latest`, `eGFR_max`, `index_month`, `eGFR_mean`, `bmi_latest`, `Creatinine_max`, `Creatinine_mean`

XGBoost tree importance top features ได้แก่ `index_year`, `missingindicator_FBS_latest`, `TC:HDL_ratio_missing_rate`, `index_month`, `hypertension_latest`, `Cholesterol_missing_rate`, `Triglyceride_missing_rate`, `eGFR_max`, `AF_latest`, `diabetes_latest`

SHAP ของ XGBoost top features ได้แก่ `index_year`, `index_month`, `bps_latest`, `age_latest`, `AF_latest`, `FBS_std`, `history_days_observed`, `eGFR_max`, `Cholesterol_min`, `bmi_latest`

ต้องเน้นว่า features เหล่านี้เป็น model signals และบางตัว เช่น calendar/missing indicators ต้องตรวจความสมเหตุสมผลก่อนตีความทางคลินิก

## 22. ทำไม feature ทางไต เช่น eGFR และ Creatinine ติดอันดับสูง

คำตอบ:

eGFR และ Creatinine อาจสะท้อน kidney function และ overall vascular/metabolic risk ซึ่งสัมพันธ์กับความเสี่ยงโรคหลอดเลือดได้

แต่ในงานนี้ยังไม่ควรสรุปเชิง causal ตรง ๆ เพราะ feature ที่ติดอันดับมีทั้งค่าจริง เช่น `eGFR_max`, `Creatinine_mean` และ missing pattern เช่น `eGFR_missing_rate`

คำตอบที่ปลอดภัยคือ โมเดลพบว่า kidney-related variables และ missingness pattern มี predictive signal ต่อ `stroke_3m` แต่ต้องตรวจ clinical validity และ missing mechanism เพิ่ม

## 23. ทำไม hypertension, AF, diabetes สำคัญ

คำตอบ:

ตัวแปรเหล่านี้เป็น known clinical risk factors ของ stroke อยู่แล้ว จึงสมเหตุสมผลที่โมเดลพบ signal จาก `hypertension_latest`, `AF_latest` และ `diabetes_latest`

อย่างไรก็ตาม ในข้อมูลนี้เป็น observational data การที่ feature สำคัญไม่ได้แปลว่าเราพิสูจน์สาเหตุ แต่เป็นความสอดคล้องระหว่าง model signal กับ clinical expectation

จุดที่ดีคือโมเดลไม่ได้พึ่งแต่ตัวแปรแปลก ๆ หรือ missing pattern อย่างเดียว แต่ยังจับ clinical risk factors ที่มีเหตุผลได้ด้วย

## 24. ทำไม medication flags อาจเสี่ยง leakage

คำตอบ:

ยาอาจสะท้อนทั้งโรคประจำตัว ความรุนแรงของโรค และการรักษาหลังแพทย์ประเมินความเสี่ยงแล้ว ถ้า timeline ไม่ชัดว่ายานั้นเกิดก่อน index date หรือก่อน outcome จริง อาจกลายเป็น post-outcome หรือ post-assessment signal

ใน feature engineering ล่าสุดควรใช้เฉพาะข้อมูลก่อนหรือ ณ index date เท่านั้น และต้องระบุ timeline ชัดเจน ถ้าอาจารย์ถาม ให้ตอบว่า medication flags ใช้ได้ในเชิง predictive feature แต่ต้อง audit เวลาอย่างเข้มก่อนใช้ production

## 25. ทำไมข้อมูล raw มี 218,772 records แต่ patient cohort เหลือ 13,031 คน

คำตอบ:

เพราะ raw data เป็น visit/record-level ขณะที่โจทย์สุดท้ายต้องการ patient-level prediction จึงต้อง aggregate ประวัติของแต่ละคนให้เป็นหนึ่งแถวต่อคนไข้

การลดจำนวนแถวไม่ได้แปลว่าทิ้งข้อมูลทั้งหมด แต่เป็นการสรุป longitudinal history เช่น latest value, mean, min, max, std, count, missing rate และ history duration เพื่อให้โมเดลใช้ข้อมูลในอดีตของคนไข้ในการทำนาย outcome ภายใน 90 วัน

## 26. train/test split ป้องกัน leakage อย่างไร

คำตอบ:

ใช้ patient-level split โดย split หลังจากข้อมูลเป็นหนึ่งแถวต่อคนไข้แล้ว และตรวจว่า `hn` ใน train กับ test ไม่ overlap กัน

นอกจากนี้ preprocessing เช่น imputation อยู่ใน sklearn pipeline ทำให้ตอน cross-validation หรือ holdout evaluation imputer fit เฉพาะ train data ไม่ใช้ข้อมูล test ในการคำนวณ median

## 27. ทำไมต้องใช้ Stratified split

คำตอบ:

เพราะ positive class น้อยมาก ถ้า split แบบ random ธรรมดา อาจทำให้ train หรือ test มีสัดส่วน stroke positive เพี้ยนได้

Stratified split ช่วยรักษาสัดส่วน `stroke_3m` ใน train/test ให้ใกล้กัน ทำให้ evaluation เสถียรกว่า และช่วยให้ metric อย่าง PR-AUC/recall เปรียบเทียบได้สมเหตุสมผล

## 28. ข้อจำกัดของงานนี้คืออะไร

คำตอบ:

ข้อจำกัดหลักมี 5 เรื่อง

1. Validation เป็น internal holdout ยังไม่ใช่ external validation
2. Positive class น้อย ทำให้ precision ต่ำและ metric แกว่งได้
3. Missing lab values สูงมาก และ missingness อาจสะท้อน workflow มากกว่าสภาวะทางชีวภาพโดยตรง
4. Calendar features เช่น `index_year` และ `index_month` ต้องตรวจ temporal drift
5. Feature importance และ SHAP อธิบายโมเดล ไม่ได้พิสูจน์สาเหตุของ stroke

ดังนั้นข้อสรุปที่เหมาะสมคือ โมเดลมี signal สำหรับ research/reporting และใช้วางแผนพัฒนาต่อ แต่ยังไม่พร้อมใช้ตัดสินใจทางคลินิก

## 29. ถ้าอาจารย์ถามว่าโมเดลพร้อมใช้จริงไหม ควรตอบอย่างไร

คำตอบ:

ยังไม่พร้อมใช้ตัดสินใจ clinical จริง

เหตุผลคือแม้ ROC-AUC 0.8850 และ recall 0.7451 จะดีพอสมควร แต่ precision ยังต่ำที่ 0.1470 และ validation ยังเป็น internal holdout ไม่ใช่ external หรือ temporal validation

คำตอบที่เหมาะสมคือ ตอนนี้เหมาะสำหรับ research reporting, exploratory risk stratification และพัฒนา workflow ต่อ ก่อนใช้งานจริงต้องทำ external validation, temporal validation, calibration, threshold policy และ clinical review

## 30. Next step ควรทำอะไร

คำตอบ:

Next step ที่ควรเสนอมี 6 อย่าง

1. ทำ temporal validation เช่น train บนปีก่อนหน้าและ test บนปีล่าสุด
2. ทดลองตัด `index_year` และ `index_month` ออก แล้วดู performance ลดลงหรือไม่
3. ทำ calibration เพิ่ม เช่น calibration model หรือ reliability analysis
4. ทำ threshold policy ตาม use case เช่น screening เน้น recall หรือ alert system เน้น precision มากขึ้น
5. เพิ่ม external validation ถ้ามีข้อมูลจากอีกช่วงเวลาหรืออีกโรงพยาบาล
6. ทำ permutation importance เพิ่ม เพื่อเทียบกับ tree importance และ SHAP

คำตอบปิดท้ายที่ดีคือ ตอนนี้งานเดินมาถูกทางแล้ว แต่ต้องพิสูจน์ robustness ก่อนนำไปใช้งานจริง

