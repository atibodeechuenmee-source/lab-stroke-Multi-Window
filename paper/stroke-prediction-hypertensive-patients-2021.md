# Accurate Prediction of Stroke for Hypertensive Patients Based on Medical Big Data and Machine Learning Algorithms

## ข้อมูลอ้างอิง

- ชื่อ paper: Accurate Prediction of Stroke for Hypertensive Patients Based on Medical Big Data and Machine Learning Algorithms: Retrospective Study
- ผู้แต่ง: Yujie Yang, Jing Zheng, Zhenzhen Du, Ye Li, Yunpeng Cai
- ปีที่เผยแพร่: 2021
- วันที่เผยแพร่: 2021-11-10
- วารสาร: JMIR Medical Informatics
- DOI: 10.2196/30277
- PMID: 34757322
- PMCID: PMC8663532

## ลิงก์อ้างอิง

- Paper: https://medinform.jmir.org/2021/11/e30277
- PubMed: https://pubmed.ncbi.nlm.nih.gov/34757322/
- DOI: https://doi.org/10.2196/30277

## เหตุผลที่เลือก paper นี้

Paper นี้เกี่ยวข้องกับโปรเจกต์ของเราโดยตรง เพราะศึกษาเรื่องการทำนายการเกิด stroke ในผู้ป่วย hypertension จากข้อมูลเวชระเบียนอิเล็กทรอนิกส์ขนาดใหญ่ และใช้ machine learning เพื่อสร้างโมเดลทำนายความเสี่ยง

ความเชื่อมโยงกับ dataset ของเรา:

- dataset ของเรามีคอลัมน์ `hypertension`
- มีข้อมูลความดันโลหิต `bps`, `bpd`
- มีข้อมูลยา `Antihypertensive_flag`
- มีข้อมูลโรคร่วม เช่น `diabetes`, `heart_disease`
- มีข้อมูลผลแล็บ เช่น cholesterol, HDL, LDL, FBS, eGFR, Creatinine

## วัตถุประสงค์ของงานวิจัย

งานวิจัยนี้ต้องการสร้างโมเดลทำนายความเสี่ยงการเกิด stroke ภายใน 3 ปี ในกลุ่มผู้ป่วย hypertension โดยใช้ข้อมูลจาก electronic medical records และ machine learning algorithms

เป้าหมายสำคัญคือทำให้สามารถคัดกรองผู้ป่วยความเสี่ยงสูงได้เร็วขึ้น เพื่อช่วยวางแผนการป้องกัน stroke ก่อนเกิดเหตุการณ์จริง

## Dataset ที่ใช้

แหล่งข้อมูลคือ Shenzhen Health Information Big Data Platform ซึ่งรวบรวมข้อมูลจากสถาบันสุขภาพจำนวนมากในเมือง Shenzhen ประเทศจีน

ข้อมูลตั้งต้น:

- ผู้ป่วย hypertension ทั้งหมด 250,788 ราย
- หลังคัดกรองตามเกณฑ์การศึกษา เหลือ 57,671 ราย
- ผู้ป่วยที่เกิด stroke ภายใน 3 ปี มี 9,421 ราย
- หลังสร้าง trend variables และคัดกรองเพิ่มเติม เหลือ cohort สำหรับ modeling 50,915 ราย
- หลังทำ stratified sampling ใช้ตัวอย่างสำหรับ modeling 19,953 ราย
- แบ่ง train/test ด้วยอัตรา 7:3

กลุ่มตัวอย่าง:

- ผู้ป่วย hypertension อายุ 30-85 ปี
- มีข้อมูล follow-up และข้อมูลเวชระเบียนเพียงพอ
- outcome คือ stroke onset ภายใน 3 ปี

## Target / Outcome

Target ของงานวิจัยคือการเกิด stroke ภายใน 3 ปี

การระบุ stroke ใช้รหัส ICD-10:

- I60 subarachnoid hemorrhage
- I61 intracerebral hemorrhage
- I62 other nontraumatic intracranial hemorrhages
- I63 cerebral infarction
- I64 stroke, not specified as hemorrhage or infarction

งานวิจัยไม่รวม I69 ซึ่งเป็น sequelae of cerebrovascular disease

## Features ที่ใช้

กลุ่ม feature ที่ใช้ใน paper ได้แก่:

- ข้อมูลประชากร เช่น อายุ เพศ
- lifestyle เช่น smoking
- family history
- follow-up records ของผู้ป่วย hypertension
- outpatient และ hospitalization records
- laboratory test results
- physiological parameters เช่น SBP, DBP, pulse pressure difference, heart rate, BMI, glucose
- medication information
- trend characteristics จากข้อมูลหลายช่วงเวลา เช่น ค่าเฉลี่ยหรือแนวโน้มของ SBP

จุดเด่นของ paper นี้คือไม่ได้ใช้แค่ค่า baseline แต่สร้าง multitemporal trend characteristics จากข้อมูลย้อนหลัง ซึ่งช่วยให้โมเดลเห็นแนวโน้มสุขภาพก่อนเกิด stroke

## Method / Model

งานวิจัยเปรียบเทียบ machine learning algorithms 4 แบบ:

- Logistic Regression
- Random Forest
- Support Vector Machine
- XGBoost

มีการทำ preprocessing เช่น:

- ลบ outliers หรือแทนเป็น null
- unify หน่วยของผลแล็บ
- จัดกลุ่มยา
- เติม missing values ของ continuous features ด้วย mean
- standardize ข้อมูลด้วย mean และ variance
- stratified sampling ตามเพศและช่วงอายุ เพื่อ balance positive/negative cases

## Evaluation Metrics

ใช้ metrics หลัก 5 ตัว:

- AUC
- Accuracy
- Recall
- Specificity
- F1-score

ยังเปรียบเทียบ performance กับ traditional risk scales ได้แก่:

- Framingham Stroke Risk Profile
- Chinese Multiprovincial Cohort Study

## ผลลัพธ์สำคัญ

ผลลัพธ์หลักของ paper:

- XGBoost ให้ผลดีที่สุดเมื่อเทียบกับโมเดลอื่น
- AUC ของ XGBoost เท่ากับ 0.9220
- โมเดล machine learning ทำได้ดีกว่า traditional risk scales
- AUC เพิ่มขึ้นประมาณ 0.17 เมื่อเทียบกับ traditional risk scales
- trend characteristics จากข้อมูลหลายช่วงเวลามีความสำคัญต่อการทำนาย stroke
- ความสัมพันธ์ของ feature ต่อ stroke มีลักษณะ nonlinear จึงเหมาะกับโมเดลเช่น XGBoost มากกว่า linear model อย่างเดียว

## ข้อจำกัดของงานวิจัย

ข้อจำกัดที่ควรระวัง:

- เป็น retrospective study จากข้อมูลเวชระเบียนจริง จึงมีปัญหา missing values และ data quality
- ข้อมูลมาจากเมือง Shenzhen ประเทศจีน อาจ generalize ไปยัง population อื่นได้จำกัด
- มีการคัดกรองผู้ป่วยจำนวนมากก่อน modeling จึงอาจทำให้ cohort สุดท้ายไม่แทนประชากรทั้งหมด
- ต้องตรวจสอบเรื่อง data leakage อย่างละเอียด หากใช้ข้อมูลที่ใกล้ช่วงเกิด stroke มากเกินไป
- แม้โมเดลมี performance สูง แต่การนำไปใช้จริงต้องมี external validation เพิ่มเติม

## สิ่งที่นำมาใช้กับโปรเจกต์ของเราได้

Paper นี้ช่วยกำหนดแนวทางงานของเราได้หลายส่วน:

- ถ้าจะสร้างโมเดลทำนาย stroke ควรเริ่มจากกลุ่มผู้ป่วย hypertension เพราะเป็นกลุ่มเสี่ยงสำคัญ
- ตัวแปรที่ dataset เรามีและควรพิจารณา ได้แก่ `age`, `sex`, `bps`, `bpd`, `bmi`, `smoke`, `drinking`, `diabetes`, `heart_disease`, `Antihypertensive_flag`, lipid labs และ kidney function labs
- ควรสร้าง feature จากข้อมูลหลายช่วงเวลา เช่น ค่าเฉลี่ย, ค่าสูงสุด, ค่าล่าสุด, ความต่างจากครั้งก่อน หรือ slope ของความดันและผลแล็บ
- XGBoost เป็น baseline model ที่น่าทดลอง เพราะเหมาะกับ nonlinear relationships และ tabular clinical data
- ควรใช้ metrics มากกว่า accuracy เช่น AUC, recall, specificity และ F1-score
- ต้องวางแผนจัดการ missing values ให้ชัดเจน เพราะ dataset ของเรามี lab missing สูง

## ความเกี่ยวข้องกับ EDA ของเรา

จาก EDA ของ dataset เรา พบว่า:

- `hypertension` ไม่มี missing values
- `bps` และ `bpd` missing ประมาณ 12-13%
- lab values เช่น `FBS`, `LDL`, `HDL`, `Cholesterol`, `eGFR`, `Creatinine` missing สูงมาก
- มี flag ยา `Antihypertensive_flag`

ดังนั้น paper นี้สนับสนุนว่าการทำ feature engineering จากข้อมูลความดัน ยา โรคร่วม และ lab trends เป็นทิศทางที่เหมาะสมสำหรับงานต่อไป

## หมายเหตุเพิ่มเติม

งานต่อไปที่ควรทำจาก paper นี้:

- ตรวจว่าข้อมูลของเรามีหลาย record ต่อผู้ป่วยหรือไม่ และสามารถสร้าง temporal features ได้อย่างไร
- นิยาม target stroke ให้ชัดจาก diagnosis columns
- ทดลองสร้าง cohort เฉพาะผู้ป่วย hypertension
- เปรียบเทียบ baseline model เช่น Logistic Regression กับ XGBoost
- ตรวจ data leakage จากยา diagnosis หรือข้อมูลหลัง outcome
