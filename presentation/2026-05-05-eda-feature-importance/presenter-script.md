# Presenter Script: EDA และ Feature Importance

## Slide 1: Dataset พร้อมวิเคราะห์ แต่ stroke เป็น minority class

สไลด์แรกคือภาพรวมของข้อมูลที่ใช้วิเคราะห์ครับ Dataset นี้มี 218,772 records และ 30 columns ครอบคลุมช่วงวันที่ 2014-10-01 ถึง 2024-06-30 จุดที่สำคัญคือ stroke records มี 5,170 records หรือ prevalence 2.36% เท่านั้น แปลว่าข้อมูลพร้อมสำหรับการวิเคราะห์ในแง่ scale แต่ target class เป็น minority class ชัดเจน ดังนั้นเวลาอ่าน metric และ feature importance ต้องจำไว้เสมอว่าข้อมูลไม่สมดุล

## Slide 2: Feature groups ครอบคลุมข้อมูลคลินิกหลายมิติ

ตัวแปรในชุดข้อมูลไม่ได้มีแค่ demographic แต่ครอบคลุมหลายมิติ ทั้งอายุและเพศ, body metrics เช่น height, body weight และ BMI, blood pressure เช่น BPS และ BPD, lab variables เช่น HDL, LDL, Triglyceride, Cholesterol, FBS และ TC:HDL ratio รวมถึง kidney markers อย่าง eGFR และ Creatinine นอกจากนี้ยังมี comorbidity flags เช่น hypertension, diabetes, heart disease, AF และ medication flags เช่น Statin, Gemfibrozil และ Antihypertensive flag ภาพรวมนี้ทำให้เราวิเคราะห์ risk profile ได้ค่อนข้างกว้าง

## Slide 3: Missing values สูงมากใน lab variables

ประเด็นใหญ่ของ EDA คือ missing values ใน lab variables สูงมากครับ FBS missing 74.14%, Triglyceride 71.99%, LDL 70.93% และ TC:HDL ratio 70.87% ตัวเลขระดับนี้ไม่ควรมองว่าเป็น noise เล็กน้อย เพราะอาจสะท้อนว่าใครถูกส่งตรวจแล็บและใครไม่ได้ตรวจ ดังนั้น missingness อาจมี information อยู่ในตัวเอง และตอน modeling จึงต้องจัดการทั้งค่าที่หายและ indicator ของการหาย

## Slide 4: ข้อมูลพื้นฐานชี้ population ที่มีความเสี่ยงสูง

จาก summary statistics ประชากรในข้อมูลมีอายุเฉลี่ย 62.78 ปี, BMI เฉลี่ย 24.91 และ systolic blood pressure เฉลี่ย 134.50 mmHg เมื่อดู disease flags จะเห็นว่า hypertension อยู่ที่ 71.15% และ diabetes อยู่ที่ 30.97% ภาพนี้บอกว่าข้อมูลมาจาก population ที่มี risk burden สูง ไม่ใช่ประชากรทั่วไปที่มีความเสี่ยงต่ำ

## Slide 5: Correlation และ outlier บอกข้อควรระวังก่อน modeling

Correlation matrix ชี้ว่ามีตัวแปรบางคู่ที่สัมพันธ์กันสูงมาก เช่น LDL กับ Cholesterol มี r=0.916, body weight กับ BMI มี r=0.883 และ eGFR กับ Creatinine มี r=-0.768 ความสัมพันธ์เหล่านี้บอกว่า feature บางตัวอาจมีข้อมูลซ้ำกันบางส่วน อีกประเด็นคือ LDL มี minimum เท่ากับ -30 ซึ่งเป็นค่าที่ควรตรวจสอบก่อนใช้งานจริง เพราะอาจเป็น data quality issue หรือรหัสพิเศษที่ถูกอ่านเป็นตัวเลข

## Slide 6: Feature importance pipeline ลด leakage จาก diagnosis/text fields

ในส่วน feature importance target ถูกสร้างจาก `PrincipleDiagnosis` โดยจับ ICD-10 กลุ่ม `I60-I69*` เป็น stroke record แต่เราไม่ใช้ `PrincipleDiagnosis`, diagnosis fields หรือ text fields เป็น feature เพราะฟิลด์เหล่านี้อาจทำให้เกิด leakage ได้ Pipeline จึงใช้เฉพาะ structured clinical variables และจัดการ missing values ด้วย median imputation พร้อม missing indicators วิธีนี้ช่วยให้โมเดลเห็นทั้งค่าของตัวแปรและ pattern การมีหรือไม่มีข้อมูล

## Slide 7: Random Forest เหมาะเป็นโมเดลหลักสำหรับ interpretation

เมื่อเทียบ holdout metrics Random Forest ได้ ROC-AUC 0.963 และ F1 0.523 ส่วน XGBoost ได้ recall สูงกว่า คือ 0.873 แต่ precision ต่ำมากที่ 0.119 สำหรับงานตีความ feature importance เราจึงใช้ Random Forest เป็นโมเดลหลัก เพราะ balance ของ precision, recall และ F1 ดีกว่าในผล holdout นี้ อย่างไรก็ตาม metric ทั้งหมดต้องอ่านร่วมกับ class imbalance ที่พูดไว้ตั้งแต่สไลด์แรก

## Slide 8: Hypertension เป็นตัวแปรสำคัญที่สุด

ผล RF feature importance ชี้ว่า hypertension เป็นตัวแปรที่สำคัญที่สุด ด้วย importance 0.254 ตามด้วย age 0.075 และ BMI 0.062 ตรงนี้สอดคล้องกับภาพ EDA ที่ population มี hypertension สูงมาก และชี้ว่า comorbidity flags มี signal ชัดเจนต่อการแยก stroke กับ non-stroke records แต่ยังเป็น model importance ไม่ใช่หลักฐาน causal effect

## Slide 9: SHAP ยืนยันสัญญาณหลักของ hypertension, diabetes, age และ medication flags

เมื่อใช้ SHAP กับ Random Forest ภาพหลักยังใกล้เคียงกันครับ hypertension มี mean absolute SHAP 0.163 เป็นอันดับหนึ่ง ตามด้วย diabetes 0.050, Antihypertensive flag 0.049 และ age 0.044 การที่ทั้ง RF importance และ SHAP ชี้ไปในทิศทางใกล้กันช่วยเพิ่มความมั่นใจว่า signal เหล่านี้มีความสำคัญต่อโมเดล แต่การตีความต้องเป็น association กับ prediction output เท่านั้น ไม่ใช่สรุปว่า feature ใดเป็นสาเหตุของ stroke

## Slide 10: ข้อสรุปและข้อควรระวัง

สรุปคือ EDA และ feature importance ให้ insight ที่ค่อนข้างชัดว่า hypertension, diabetes, age, BMI และ medication flags เป็นกลุ่มสัญญาณสำคัญ แต่ต้องระวัง 4 เรื่องหลัก คือ missing values สูงมากใน lab variables, class imbalance เพราะ stroke มีเพียง 2.36%, leakage จาก diagnosis หรือ text fields และการตีความ feature importance แบบ causal ก้าวต่อไปควรตรวจด้วย permutation importance, ทำ temporal validation และต่อยอดไปยัง patient-level dataset เพื่อให้เหมาะกับโจทย์ prediction ในอนาคตมากขึ้น
