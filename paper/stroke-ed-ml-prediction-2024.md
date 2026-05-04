# Machine Learning-Based Prediction of Stroke in Emergency Departments

## ข้อมูลอ้างอิง

- ชื่อ paper: Machine Learning-Based Prediction of Stroke in Emergency Departments
- ผู้แต่ง: Vida Abedi, Debdipto Misra, Durgesh Chaudhary, Venkatesh Avula, Clemens M. Schirmer, Jiang Li, Ramin Zand และคณะ
- ปีที่เผยแพร่: 2024
- วันที่เผยแพร่: 2024-04-01
- วารสาร: Therapeutic Advances in Neurological Disorders
- DOI: 10.1177/17562864241239108
- URL: https://doi.org/10.1177/17562864241239108

## ลิงก์อ้างอิง

- Paper: https://journals.sagepub.com/doi/10.1177/17562864241239108
- DOI: https://doi.org/10.1177/17562864241239108

## เหตุผลที่เลือก paper นี้

Paper นี้เหมาะกับโปรเจกต์ของเราเพราะเป็นงานปี 2024 ที่ใช้ข้อมูลเวชระเบียนอิเล็กทรอนิกส์จริงจากหลายโรงพยาบาล เพื่อสร้างโมเดลช่วยทำนายหรือ flag ผู้ป่วย ischemic stroke ในห้องฉุกเฉิน งานนี้มีทั้ง structured data เช่น อายุ โรคร่วม lab ความดัน และ medication history รวมถึง unstructured data จาก provider notes ซึ่งช่วยให้เห็นแนวทางต่อยอดจากข้อมูล tabular ของเราไปสู่ clinical decision support system ได้

อีกเหตุผลสำคัญคือ paper นี้มีการทำ temporal/prospective validation แยกช่วงก่อนและหลัง COVID-19 ทำให้เป็นตัวอย่างที่ดีของการประเมินความเสถียรของโมเดลเมื่อเวลาหรือบริบทการรักษาเปลี่ยนไป ซึ่งตรงกับแนวทางพัฒนาโปรเจกต์ของเราให้พร้อมใช้งานจริงมากขึ้น

## วัตถุประสงค์ของงานวิจัย

งานวิจัยต้องการทดสอบว่า machine learning สามารถช่วยลดการวินิจฉัย stroke ผิดพลาดใน emergency department ได้หรือไม่ โดยสร้างโมเดลจากข้อมูล EHR สองกลุ่ม:

- ข้อมูล structured ก่อนเกิดเหตุ เช่น demographics, medical history, laboratory results, social/family history และ medication history
- ข้อมูล unstructured ณ เวลามาห้องฉุกเฉิน คือ provider notes ช่วง initial history of present illness

เป้าหมายหลักคือช่วยคัดกรอง ischemic stroke จาก non-stroke หรือ stroke mimic เพื่อสนับสนุน stroke alert system ในระบบโรงพยาบาล

## Dataset ที่ใช้

- แหล่งข้อมูล: Geisinger health system ใน Pennsylvania, United States
- จำนวนโรงพยาบาล: 13 แห่ง
- ช่วงเวลา: กันยายน 2003 ถึง มกราคม 2021
- จำนวน encounters ทั้งหมดที่ใช้สร้างและ validate โมเดล: 56,452 patient encounters
- Development cohort: 49,155 encounters
- Cases: 8,900 ischemic stroke patients
- Controls: 40,255 non-stroke controls
- กลุ่ม control มี stroke mimics ประมาณ 7,232 encounters หรือ 18.0% ของ control group

เกณฑ์ case group คือผู้ป่วยที่มาห้องฉุกเฉินหรือถูก transfer เป็น inpatient มี primary discharge diagnosis เป็น ischemic stroke มี brain MRI และมี encounter duration มากกว่า 24 ชั่วโมง ส่วน control คือผู้ป่วยที่มาห้องฉุกเฉินหรือ inpatient มี encounter duration มากกว่า 24 ชั่วโมง และมี head CT โดย exclude TIA, intracranial hemorrhage และ trauma-related diagnosis

## Target / Outcome

Outcome คือการจำแนกผู้ป่วยว่าเป็น ischemic stroke หรือ non-stroke ในบริบท emergency department

ในแง่โปรเจกต์ของเรา งานนี้เกี่ยวข้องกับ ICD group `I60-I69` เพราะเป็นกลุ่ม cerebrovascular diseases แต่ paper นี้จำกัด focus ที่ ischemic stroke และ exclude intracranial hemorrhage/TIA บางกลุ่ม จึงควรนำแนวคิดไปใช้โดยระวังนิยาม target ให้ชัดเจนว่าเรากำลังทำนาย stroke ทุกชนิดจาก `I60-I69*` หรือเฉพาะ ischemic stroke

## Features สำคัญ

กลุ่ม feature ที่ใช้ใน structured model:

- อายุและเพศ
- ความดันโลหิต systolic/diastolic
- BMI
- lab เช่น hemoglobin, HbA1c, LDL, platelet count, white blood cell count, serum creatinine
- ระยะเวลาระหว่าง outpatient visit ล่าสุดกับ index encounter
- medical history เช่น atrial fibrillation/flutter, hypertension, myocardial infarction, diabetes, dyslipidemia, congestive heart failure, chronic kidney disease, previous ischemic stroke, depression, anxiety disorder
- medication history เช่น aspirin, clopidogrel, warfarin, statins, antihypertensives
- family history เช่น family history of stroke และ heart disease
- insurance type

Feature importance เฉลี่ยจากหลาย algorithm พบว่า feature สำคัญที่สุดคือ age ตามด้วย hemoglobin, HbA1c และ systolic blood pressure ส่วน lab อื่นอย่าง creatinine, white blood cell count, platelet count และ BMI ก็มีบทบาทสำคัญ

## Method / Model

งานวิจัยแบ่ง pipeline เป็น 2 ส่วน:

1. Structured pre-event EHR model
2. Unstructured ED provider-note NLP model

สำหรับ structured data ใช้โมเดล:

- Logistic Regression / Generalized Linear Model
- XGBoost
- Random Forest

สำหรับ provider notes ใช้ NLP pipeline:

- ใช้ Apache cTAKES เพื่อ extract clinical concepts จาก initial HPI notes
- ใช้ UMLS dictionaries
- จัดการ polarity/negation เช่น ระบุว่าผู้ป่วย "ไม่มี" อาการบางอย่าง
- เลือก informative Concept Unique Identifiers หรือ CUIs
- ทดลอง latent semantic indexing เพื่อทำ dimensionality reduction

โมเดลจาก notes ใช้:

- Logistic Regression / GLM
- XGBoost
- Support Vector Machine
- Random Forest

การ tune model ใช้ parameter grid และ five-fold repeated cross-validation จำนวน 5 repeats

## การจัดการ Missing Values

งานวิจัยพบ missing ใน lab, ระยะเวลาระหว่าง outpatient visit กับ index encounter และ BMI โดยใช้ MICE หรือ Multivariate Imputation by Chained Equations แยกทำใน training และ testing set เพื่อลด data leakage

สำหรับตัวแปรที่ missing สูง เช่น HbA1c และ LDL มีการเพิ่ม indicator variable เพื่อบอกว่า feature นั้น missing หรือไม่ แนวคิดนี้สำคัญกับ dataset ของเรา เพราะ lab หลายตัวมี missing สูงมาก การเพิ่ม missing indicator อาจช่วยให้โมเดลเรียนรู้ pattern การตรวจ lab ที่สัมพันธ์กับความเสี่ยงได้

## Evaluation Metrics

Metrics ที่ใช้:

- AUROC
- Accuracy
- Positive Predictive Value หรือ PPV
- Negative Predictive Value หรือ NPV
- Sensitivity
- Specificity
- Confusion matrix สำหรับโมเดล NLP ที่ดีที่สุด

จุดเด่นคือมีการประเมินแบบ unseen test set และ prospective/temporal validation แยก cohort ก่อนและหลัง COVID-19

## ผลลัพธ์สำคัญ

ผลจาก structured pre-event EHR:

- โมเดล structured data ทั้ง 3 ตัวมี accuracy และ AUROC มากกว่า 0.88
- XGBoost ทำได้ดีที่สุดจาก structured data โดย accuracy ประมาณ 0.89 และ AUROC 0.92
- Random Forest มี AUROC 0.91 และ PPV สูงสุดประมาณ 0.80
- Logistic Regression มี AUROC 0.88

ผลจาก provider notes:

- โมเดลจาก notes ให้ AUROC ช่วง 0.95 ถึง 0.99 บน unseen testing dataset
- ใน prospective validation โมเดลมี AUROC ช่วง 0.93 ถึง 0.99
- sensitivity สูงสุดประมาณ 0.90 และ specificity สูงสุดประมาณ 0.99
- ใน case study ผู้ป่วย stroke ที่เคยถูกวินิจฉัยพลาด 5 ราย โมเดล NLP + RF, NLP + SVM และ NLP + XGB จำแนกถูกทั้ง 5 ราย

## ข้อจำกัดของงานวิจัย

- เป็นข้อมูลจาก health system เดียว แม้จะมี 13 โรงพยาบาล แต่ยังต้อง external validation กับระบบโรงพยาบาลอื่น
- clinical notes มี style และ vocabulary เฉพาะของแต่ละโรงพยาบาล จึงอาจต้องปรับ preprocessing ใหม่เมื่อนำไปใช้ที่อื่น
- EHR มี noise และ missing ตามธรรมชาติ
- pre-event data อาจใช้ไม่ได้ดีในพื้นที่ที่ผู้ป่วยย้ายเข้าออกระบบบริการบ่อย หรือไม่มี longitudinal data เพียงพอ
- ยังจับผู้ป่วยที่ออกจาก ED ก่อน workup เสร็จหรือก่อนลง diagnosis ไม่ได้

## สิ่งที่นำมาใช้กับโปรเจกต์ของเราได้

- เพิ่ม missing indicator ให้ lab ที่ missing สูง เช่น HbA1c, LDL, HDL, Cholesterol, eGFR, Creatinine และ FBS
- ใช้ temporal validation หรือ time-based split เพิ่มเติม ไม่พึ่งแค่ random train/test split หรือ Stratified K-Fold
- เปรียบเทียบ Random Forest, XGBoost และ Logistic Regression ต่อไป เพราะ paper นี้พบว่า XGBoost แข็งแรงกับ structured EHR
- เพิ่ม feature จาก encounter timeline เช่น จำนวนวันจาก visit ก่อนหน้า หรือ aggregation ย้อนหลัง ถ้า dataset มีหลาย visit ต่อผู้ป่วย
- แยกนิยาม target ให้ชัดว่าต้องการทำนาย `I60-I69*` ทั้งกลุ่ม หรือเฉพาะ ischemic stroke เช่น `I63*`
- ถ้ามีข้อมูล chief complaint หรือ clinical note ในอนาคต อาจเพิ่ม NLP pipeline เพื่อช่วยจับ stroke mimic และลด false negative
- รายงานผลควรมี AUROC, PR-AUC, recall/sensitivity, specificity, PPV/precision, NPV และ confusion matrix เพราะ stroke เป็นเหตุการณ์ที่มี class imbalance

## หมายเหตุเพิ่มเติม

ระหว่างค้น paper ปี 2024 พบงาน Scientific Reports บางชิ้นเกี่ยวกับ stroke prediction ที่ถูกระบุว่าเป็น retracted article ในปี 2026 จึงไม่เลือกใช้เป็น paper หลักสำหรับสรุปนี้ เพื่อหลีกเลี่ยงการอ้างอิงงานที่ความน่าเชื่อถือลดลง
