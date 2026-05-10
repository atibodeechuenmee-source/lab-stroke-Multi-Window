# Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction

> เวอร์ชันแปลไทยแบบคง technical terms: ไฟล์นี้สร้างจาก `Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.th.md` โดยปรับคำแปลให้คงคำอังกฤษที่ใช้ในงานวิจัยและ implementation มากขึ้น เพื่อให้อ่านคู่กับ code และ docs/pipeline ได้ตรงกัน

## Translation Policy

คำที่ตั้งใจคงเป็นภาษาอังกฤษหรือใช้แบบผสมไทย-อังกฤษ:

- `stroke`, `stroke-risk prediction`, `machine learning`, `EHR`
- `single-shot baseline`, `temporal features`, `temporal window`, `retrospective observation window`
- `reference date`, `pre-reference`, `post-reference`, `data leakage`
- `FIRST/MID/LAST windows`, `prediction window`, `overlapping windows`
- `feature extraction`, `feature selection`, `feature engineering`, `Extract Set 1/2/3`
- `ANOVA F-test`, `PCA`, `ANOVA+PCA`, `Logistic Regression`, `LOOCV`, `McNemar's test`
- `sensitivity`, `specificity`, `G-Mean`, `AUC`, `class imbalance`
- clinical variables เช่น `BPS`, `BPD`, `HDL`, `LDL`, `FBS`, `BMI`, `eGFR`, `Creatinine`, `TC:HDL ratio`

---

## Paper Translation

Authors: Chanon Thansawd, Eri Sato-Shimokawara, Suwanna Rasmequan, Sittisak Saechueng, Yosuke Fukuchi, Waranrach Viriyavit, Peerasak Painprasit, Nobuyuki Nishiuchi

Affiliation: Faculty of Informatics, Burapha University, Thailand และ Graduate School of Systems Design, Tokyo Metropolitan University, Japan

## Abstract

stroke เป็นภาระด้านสุขภาพที่สำคัญในระดับโลก stroke-risk prediction ตั้งแต่ระยะเริ่มต้นมีความจำเป็นต่อการลดความพิการและการเสียชีวิต วิธีการด้าน machine learning ที่มีอยู่ส่วนใหญ่อาศัยข้อมูลทางคลินิกแบบ single-shot ซึ่งไม่สามารถจับพลวัตด้านสุขภาพ longitudinal ที่เกิดขึ้นก่อนการเริ่มต้นของ stroke ได้ เพื่อแก้ข้อจำกัดนี้ งานศึกษานี้สร้าง temporal representations ในสามหน้าต่างสังเกตการณ์ย้อนหลัง statistical, temporal, and cross-window features ถูกสร้างขึ้นเพื่อจับทั้งความแปรปรวนระยะสั้นและแนวโน้มทางสรีรวิทยาระยะยาว และมีการออกแบบชุด features เชิงลำดับชั้นสามชุดเพื่อประเมินผลของความซับซ้อนที่เพิ่มขึ้นในการทำ feature engineering

งานนี้ใช้ ANOVA F-test และ Principal Component Analysis (PCA) สำหรับ dimensionality reduction จากนั้นประเมินสมรรถนะของโมเดลด้วย Logistic Regression ร่วมกับ Leave-One-Out Cross-Validation (LOOCV) ภายใต้สภาวะที่ข้อมูลมี class imbalance อย่างรุนแรง ผลลัพธ์แสดงว่า temporal model ให้ผลดีกว่า single-shot baseline โดยมีค่า G-Mean สูงสุดเท่ากับ 0.638 McNemar's test ยังยืนยันเพิ่มเติมว่า temporal representations ทำให้เกิดการปรับปรุงอย่างมีนัยสำคัญทางสถิติ และชี้ว่าพฤติกรรมการทำนายระหว่าง PCA และ ANOVA แตกต่างกันเพียงเล็กน้อย โดยรวมแล้ว ผลการศึกษาบ่งชี้ว่าการใช้ temporal dataช่วยเพิ่มประสิทธิภาพ stroke-risk prediction ระยะเริ่มต้นอย่างมีนัยสำคัญ และให้ความสามารถด้าน decision support ที่น่าเชื่อถือกว่าวิธีที่ใช้ข้อมูลจากจุดเวลาเดียวแบบดั้งเดิม

Keywords: component, stroke prediction, temporal features, single-shot data, machine learning, logistic regression, feature engineering, PCA, F-ANOVA

## I. Introduction

stroke ยังคงเป็นปัญหาสุขภาพระดับโลกที่สำคัญ โดยในยุโรปมีผู้ป่วยรายใหม่มากกว่า 1.3 ล้านรายต่อปี และทั่วโลกมีผู้เสียชีวิตหนึ่งรายทุก ๆ สี่นาที ภาวะนี้มักนำไปสู่ความพิการระยะยาว ค่าใช้จ่ายด้านสาธารณสุขจำนวนมาก และการเสียชีวิตก่อนวัยอันควร อย่างไรก็ตาม มีการประเมินว่าประมาณ 40% ของผู้ป่วย stroke สามารถป้องกันได้ด้วยการตรวจพบตั้งแต่ระยะเริ่มต้นและการแทรกแซงอย่างทันท่วงที [1], [2]

Machine learning (ML) แสดงศักยภาพที่น่าสนใจสำหรับ stroke-risk prediction งานวิจัยก่อนหน้าได้สำรวจโมเดล ML หลายแบบโดยใช้ features ด้านประชากรศาสตร์ ทางคลินิก และพฤติกรรม Wang และคณะประยุกต์ใช้ XGBoost และ Logistic Regression ร่วมกับการคัดเลือก features โดยอิง feature importance สำหรับการทำนายการเสียชีวิต ผลลัพธ์แสดงว่า XGBoost ให้ผลดีกว่า Logistic Regression โดยได้ accuracy 98.1% และ AUC 0.95 เทียบกับ accuracy 83.0% และ AUC 0.77 [3] Emon และคณะเปรียบเทียบตัวจำแนก ML จำนวนสิบแบบ และพบว่า weighted voting ensemble ให้สมรรถนะสูงสุด โดยได้ accuracy 97% พร้อม false positives และ false negatives ที่ต่ำมาก [4] Das และคณะประเมินอัลกอริทึมเก้าแบบ ได้แก่ support vector machines (SVM), K-nearest neighbor (KNN), XGBoost, AdaBoost, Random Forest, Decision Tree, LightGBM และ Logistic Regression และรายงานว่า Random Forest เป็นโมเดลที่ดีที่สุดโดยมี accuracy 98.4% [5] แนวทาง ensemble ก็ให้ผลดีเช่นกันตามรายงานของ Dritsas และ Trigka ซึ่งได้ AUC 98.9% ด้วย stacking-based framework [6] ล่าสุด Chowdhury และคณะได้นำ lag features และ rolling statistical functions เข้าไปใน XGB-RS model ที่เสริมด้วยเทคนิค XAI โดยได้ accuracy 98.06% และ specificity 99.12% [7]

แม้ว่าผลลัพธ์เหล่านี้จะสูงมาก แต่โมเดลส่วนใหญ่ยังพึ่งพาข้อมูลแบบ cross-sectional หรือ single-shot อย่างมาก โดยผู้ป่วยแต่ละรายให้ข้อมูลทางคลินิกเพียงหนึ่งระเบียน การแทนข้อมูลแบบนี้ละเลยพลวัตด้านสุขภาพ longitudinal เช่น ความดันโลหิตที่สูงขึ้น ระดับไขมันที่ผันผวน หรือการทำงานของไตที่ลดลง ซึ่งมักเกิดขึ้นก่อนการเริ่มต้นของ stroke ดังนั้น single-shot models จึงไม่สามารถใช้ประโยชน์จากความสามารถของ ML ในการจับรูปแบบไม่เชิงเส้นและขึ้นกับเวลาได้เต็มที่ ส่งผลให้ความทนทานทางคลินิกของโมเดลมีข้อจำกัด

ในระบบบริการสุขภาพจริง electronic health records (EHR) แบบ longitudinal ให้ข้อมูล temporal ที่สมบูรณ์กว่า แต่ก็นำมาซึ่งความท้าทายเพิ่มเติม แตกต่างจากชุดข้อมูลวิจัยที่ผ่านการจัดเตรียมมาอย่างดี EHR จริงมักไม่สม่ำเสมอ ไม่สมบูรณ์ และมีความหลากหลาย ผู้ป่วยเข้ารับบริการในช่วงเวลาที่ไม่เท่ากัน ทำให้ระเบียน temporal ไม่ align กันและมีระยะห่างระหว่าง visit ไม่สม่ำเสมอ นอกจากนี้ การตรวจทางห้องปฏิบัติการที่สำคัญ เช่น lipid profiles, glucose levels และ estimated glomerular filtration rate (eGFR) ไม่ได้ถูกเก็บในทุก visit ทำให้หลาย observation windows มีข้อมูลบางส่วนหรือขาดหายทั้งหมด ปัญหาเหล่านี้ทำให้การสร้าง temporal features ที่น่าเชื่อถือซับซ้อนขึ้น และขัดขวางการพัฒนาโมเดลที่เหมาะสมต่อการนำไปใช้ทางคลินิก

จากข้อจำกัดเหล่านี้ งานศึกษานี้เสนอ temporal-feature framework ที่จัดระเบียบ longitudinal EHR data ให้เป็น multi-window representations แบบมาตรฐาน เพื่อจับ trajectory ด้านสุขภาพที่มีความหมาย แนวทางที่เสนอนี้ถูกนำไปเปรียบเทียบกับ traditional single-shot baselines เพื่อวัดมูลค่าเชิงทำนายที่เพิ่มขึ้นจากการสร้างโมเดล temporal patterns การแก้ทั้งช่องว่างเชิงวิธีวิทยาและความท้าทายในทางปฏิบัติของ real-world EHR ทำให้งานนี้มีเป้าหมายในการผลักดัน stroke-risk prediction ไปสู่โมเดลที่ทนทานทางคลินิกและรับรู้มิติเวลาได้มากขึ้น

## II. วัสดุและวิธีการ

### A. การเก็บรวบรวมข้อมูล

งานศึกษานี้ใช้ชุดข้อมูลทางคลินิกจริงที่ประกอบด้วย electronic health records จำนวน 245,978 ระเบียน จากผู้ป่วย 19,473 รายที่โรงพยาบาลโชคชัย ประเทศไทย ระหว่างเดือนตุลาคม 2014 ถึงเดือนมิถุนายน 2024 ในบรรดาผู้ป่วยเหล่านี้ มี 16,696 ราย (85.7%) ที่ไม่มีประวัติการเกิด stroke ขณะที่ 2,777 ราย (14.3%) เคยเกิด stroke อย่างน้อยหนึ่งครั้ง เหตุการณ์ stroke ถูกระบุโดยใช้ International Classification of Diseases, 10th Revision (ICD-10) จากรหัส I60-I68 [8]

ชุดข้อมูลต้นฉบับมี 45 attributes ในงานศึกษานี้เลือกตัวแปรที่มีความสำคัญทางคลินิกและเป็นที่ทราบว่าเกี่ยวข้องกับความเสี่ยง stroke จำนวน 16 ตัวแปร [3-10] ได้แก่ systolic blood pressure (BPS), diastolic blood pressure (BPD), high-density lipoprotein (HDL), total cholesterol, triglycerides, body mass index (BMI), eGFR, gender, age, atrial fibrillation (AF), alcohol consumption status, smoking status, creatinine, dispensed medications, principal diagnosis และ comorbidity diagnosis (ICD-10 codes)

### B. การคัดเลือกข้อมูล

ในงานศึกษานี้ ข้อมูลผู้ป่วยถูกคัดเลือกด้วยเกณฑ์ด้านการวินิจฉัย เวลา และความครบถ้วนที่เข้มงวด เพื่อให้สามารถทำ multi-window temporal feature extraction ได้อย่างน่าเชื่อถือ ผู้ป่วย stroke ถูกระบุด้วย ICD-10 codes I60-I68 โดยกำหนด `reference date` เป็นเหตุการณ์ stroke ครั้งแรกสำหรับผู้ป่วย stroke และเป็น clinical visit ครั้งสุดท้ายสำหรับผู้ป่วย non-stroke ข้อมูลทุกระเบียนหลัง `reference date` ถูกลบออกเพื่อกำจัด post-event leakage

เนื่องจาก EHR จริงมีลักษณะไม่สม่ำเสมอและไม่สมบูรณ์ จึงมีการกำหนดโครงสร้างเวลาแบบมาตรฐาน โดยสร้าง retrospective windows สามช่วงสำหรับผู้ป่วยแต่ละราย (Fig. 1) สำหรับผู้ป่วย stroke หน้าต่าง FIRST, MID และ LAST สอดคล้องกับช่วง 21-9, 18-6 และ 15-3 เดือนก่อนเหตุการณ์ stroke ตามลำดับ สำหรับผู้ป่วย non-stroke ใช้ช่วงเวลาเดียวกันโดยอ้างอิงจาก last visit framework นี้ทำให้ temporal alignment มีความสม่ำเสมอในบริบทที่ visit patterns และ data availability แตกต่างกัน

รูปที่ 1: การสร้าง fixed retrospective temporal windows จำนวนสามช่วง

รูปที่ 2: completeness constraint ที่ทำให้มั่นใจว่ามี clinical feature coverage ครบถ้วนในแต่ละ temporal window

จากนั้นมีการใช้ completeness constraint เพื่อให้ temporal features สามารถคำนวณได้อย่างสม่ำเสมอในทุกบุคคล (Fig. 2) ผู้ป่วยแต่ละรายต้องผ่านเงื่อนไขสองข้อ:

1. แต่ละ window (FIRST, MID, LAST) ต้องมี clinical visit อย่างน้อยหนึ่งครั้ง
2. core clinical variables ทุกตัวที่จำเป็นสำหรับ temporal feature extraction ต้องมีอยู่ในทุก window แม้ window นั้นจะมีเพียง visit เดียว

ข้อจำกัดนี้ช่วยลดผลกระทบของข้อมูลสูญหาย และทำให้ temporal representations สามารถเปรียบเทียบกันได้ระหว่างผู้ป่วย

หลังจากใช้เกณฑ์ temporal alignment และ completeness ทั้งหมดแล้ว เหลือผู้ป่วยใน final dataset จำนวน 3,976 ราย ประกอบด้วยผู้ป่วย stroke 148 ราย และ non-stroke 3,828 ราย cohort ที่ได้จึงเป็นพื้นฐานที่สอดคล้อง temporal และมี feature ครบถ้วนสำหรับการดึง statistical และ temporal representations ใน downstream modeling

### C. การเตรียมข้อมูล

การเตรียมข้อมูลดำเนินการเพื่อให้ได้ clinical records ที่สะอาดและสม่ำเสมอก่อนทำ temporal segmentation ข้อมูลที่ระบุตัวบุคคลได้ทั้งหมดถูกลบออก โดยคงไว้เฉพาะ hospital numbers (HN) ในฐานะ anonymized identifiers ข้อมูลถูก harmonized ด้วยการทำ date formats, measurement units และ variable names ให้เป็นมาตรฐาน ขณะที่ค่าที่ไม่สมเหตุสมผลหรือระเบียนซ้ำถูกแทนด้วย missing values Binary clinical attributes เช่น atrial fibrillation, smoking, alcohol use, heart disease, hypertension, diabetes, statin และ antihypertensive use [9], [10] ถูกเข้ารหัสใน schema `{0,1}` และ diagnostic fields ถูก normalize ด้วย ICD-10 codes ขั้นตอนเหล่านี้สร้าง dataset ที่เป็นมาตรฐานและน่าเชื่อถือสำหรับการสร้าง temporal windows และการดึง features

### D. การดึง features

ในงานศึกษานี้ การดึง features ทำโดยรวมตัวแปรที่เกี่ยวข้องทางคลินิก ดัชนีชีวเคมีที่สร้างขึ้นใหม่ statistical descriptors และ temporal dynamics ที่ได้จาก retrospective observation windows สามช่วง (FIRST, MID, LAST) ก่อนอื่นมีการคำนวณ cardiovascular biomarker ที่สร้างขึ้นคือ total cholesterol-to-HDL ratio (TC:HDL) [11] ตามสมการ (1) เนื่องจากเป็นตัวบ่งชี้ lipid imbalance และความเสี่ยง stroke ที่ใช้กันอย่างแพร่หลาย:

```text
TC:HDL = Total Cholesterol / HDL (1)
```

สำหรับตัวแปรเชิงตัวเลขทางคลินิกสิบตัว ได้แก่ BPS, BPD, HDL, LDL, FBS, BMI, eGFR, creatinine, total cholesterol และ triglycerides มีการคำนวณ statistical descriptors หกแบบ ได้แก่ mean, minimum, maximum, standard deviation, first value และ last value จากค่าที่วัดได้ทั้งหมดภายในสาม windows features เหล่านี้จับ central tendency, variability และ short-term fluctuations ได้มากกว่าการแทนข้อมูลจากจุดเวลาเดียว

เพื่ออธิบาย long-term physiological trends มีการสร้าง temporal descriptors โดยเปรียบเทียบค่าระหว่าง FIRST และ LAST windows ได้แก่ delta change, slope of change, cross-window differences ของ minimum และ maximum values และ differences in measurement counts Delta change และ slope คำนวณดังนี้:

```text
∆X = X_LAST - X_FIRST (2)
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST) (3)
```

Temporal features เหล่านี้จับ longitudinal trends เช่น ความดันโลหิตที่เพิ่มขึ้นหรือการทำงานของไตที่ลดลง ซึ่งไม่สามารถสังเกตได้จาก clinical measurements แบบแยกเดี่ยว Demographic และ categorical variables ได้แก่ age, sex, smoking, drinking, atrial fibrillation ถูกดึงจาก clinical record ล่าสุด ร่วมกับ clinical risk factors เพิ่มเติมอีกหกตัว ได้แก่ diabetes, hypertension, heart disease, statin use, antihypertensive use และ TC:HDL ratio features ทั้งหมดถูกจัดกลุ่มเป็นสาม hierarchical sets:

- Extract Set 1 (35 features): core demographic และ clinical variables (10 numerical variables x 3 temporal windows + 5 categorical features)
- Extract Set 2 (115 features): ขยาย Set 1 ด้วย detailed temporal และ statistical descriptors สำหรับ numerical variable แต่ละตัว ได้ทั้งหมด 5 + (11 x 10) = 115 features ซึ่งประกอบด้วย demographic และ categorical variables 5 ตัว และ derived features 110 ตัวที่สร้างจาก temporal/statistical descriptors 11 แบบบน numeric clinical variables 10 ตัว
- Extract Set 3 (121 features): ขยาย Set 2 โดยเพิ่ม clinical และ biochemical risk factors อีกหกตัว ได้แก่ diabetes, hypertension, heart disease, statin use, antihypertensive use และ TC:HDL ratio ทำให้ได้ feature set ขนาด 115 + 6 = 121 features

รายการ features แสดงใน Table I

### Table I. รายการ features และคำอธิบาย

| Category | Feature | Type |
|---|---|---|
| Core Feature | Gender | Categorical |
| Core Feature | Age | Numerical |
| Core Feature | Atrial Fibrillation (AF) | Categorical |
| Core Feature | Alcohol Drinking Status | Categorical |
| Core Feature | Smoking Status | Categorical |
| Core Feature | Systolic Blood Pressure (BPS) | Numerical |
| Core Feature | Diastolic Blood Pressure (BPD) | Numerical |
| Core Feature | High-Density Lipoprotein (HDL) | Numerical |
| Core Feature | Low-Density Lipoprotein (LDL) | Numerical |
| Core Feature | Fasting Blood Sugar (FBS) | Numerical |
| Core Feature | Body Mass Index (BMI) | Numerical |
| Core Feature | Estimated Glomerular Filtration Rate (eGFR) | Numerical |
| Core Feature | Creatinine | Numerical |
| Other Feature | Dispensed drugs | Categorical |
| Other Feature | Principal diagnosis | Categorical |
| Other Feature | Comorbidity diagnosis | Categorical |
| Feature Extraction | Heart disease | Categorical |
| Feature Extraction | Hypertension | Categorical |
| Feature Extraction | Diabetes | Categorical |
| Feature Extraction | Statin flag | Categorical |
| Feature Extraction | Antihypertensive flag | Categorical |
| Feature Extraction | TC:HDL ratio | Numerical |

### E. การคัดเลือก features

การคัดเลือก features ใช้กระบวนการ supervised สองขั้นตอน ขั้นแรก ใช้ ANOVA F-test เพื่อจัดอันดับ numerical features ตาม discriminative power โดยให้ความสำคัญสูงกับ features ที่มี p-values ต่ำกว่า [12] จากนั้นใช้ forward top-k strategy โดยเพิ่ม features ตามลำดับ ranking ของ ANOVA ทีละชุด เช่น k = 5, 10, 15, ... Logistic Regression พร้อม class weighting ถูก train บนแต่ละ subset และเลือก k ที่เหมาะสมที่สุดจากค่า G-Mean สูงสุดภายใต้ LOOCV กระบวนการนี้ทำแยกสำหรับ Extract Set 1, Extract Set 2 และ Extract Set 3 เพื่อประเมินว่าความซับซ้อนของ feature engineering ส่งผลต่อ supervised feature reduction อย่างไร

### F. dimensionality reduction

Principal Component Analysis (PCA) ถูกใช้เพื่อลด redundancy ระหว่าง temporal features ที่มีความสัมพันธ์กัน และช่วยเพิ่ม model generalization [13] Numerical features ถูก standardize ก่อนทำ PCA และจำนวน components k ถูกเพิ่มทีละระดับ เช่น k = 5, 10, 15, ... Logistic Regression พร้อม class weighting ถูก train บนแต่ละ PCA-transformed set และใช้ LOOCV ร่วมกับ G-Mean เพื่อกำหนด k ที่เหมาะสมที่สุด PCA ถูกใช้แยกกันใน Extract Sets 1-3 เพื่อประเมินประสิทธิผลของวิธีนี้ในระดับความซับซ้อนของ features ที่แตกต่างกัน และเพื่อเปรียบเทียบโดยตรงกับแนวทาง supervised ANOVA-based

### G. โมเดลจำแนกประเภท

งานทำนายความเสี่ยง stroke ถูกกำหนดเป็น binary classification problem เนื่องจาก dataset มี class imbalance สูง จึงใช้ Logistic Regression ที่กำหนด `class_weight = 'balanced'` เพื่อลด bias ต่อ majority class Logistic Regression ถูกเลือกเพราะตีความได้ มีประสิทธิภาพ และเหมาะต่อ clinical decision support นอกจากนี้ยังใช้ Leave-One-Out Cross-Validation (LOOCV) โดยให้ผู้ป่วยแต่ละรายถูกกันออกเป็น test case หนึ่งครั้ง เพื่อให้มี patient-level independence ป้องกัน data leakage และให้การประมาณ model generalization ที่น่าเชื่อถือ

ใช้ performance metrics สำคัญสามตัว ได้แก่ sensitivity, specificity และ geometric mean (G-Mean) Sensitivity และ specificity วัดความสามารถของโมเดลในการระบุผู้ป่วย stroke และ non-stroke ได้ถูกต้องตามลำดับ ส่วน G-Mean ซึ่งเป็นสมดุลระหว่างสองค่านี้ นิยามดังนี้:

```text
G-Mean = sqrt(Sensitivity x Specificity) (4)
```

G-Mean ถูกเน้นเป็นพิเศษเพราะให้การประเมินที่ยุติธรรมกว่า overall accuracy สำหรับ medical datasets ที่มี class imbalance สูง โดยทำให้มั่นใจว่าโมเดลทำงานได้ดีทั้งกับ minority class (stroke) และ majority class (non-stroke)

สุดท้าย มีการใช้ McNemar's test เพื่อประเมิน paired classifiers สองตัว โดยพิจารณากรณีที่โมเดลหนึ่งทำนายถูกขณะที่อีกโมเดลทำนายผิด

## III. ผลลัพธ์และอภิปราย

### A. การเปรียบเทียบระหว่าง Single-Shot Baseline และ Temporal

ในงานศึกษานี้ single-shot baseline ใช้เพียง clinical record ล่าสุดเท่านั้น สำหรับการวิเคราะห์แรก ผู้วิจัยเปรียบเทียบ temporal model ที่สร้างจาก retrospective windows สามช่วงกับ single-shot baseline แตกต่างจาก single-shot approach การแทนข้อมูล temporal สามารถจับ longitudinal health patterns เช่น biomarker trends และการเปลี่ยนแปลงทางสรีรวิทยาอย่างค่อยเป็นค่อยไป ดังแสดงใน Table II temporal model (Extract Set 1 - LAST) ได้ G-Mean สูงกว่า (0.627) single-shot baseline (0.611) แม้ความต่างจะไม่มาก แต่มีการใช้ McNemar's test เพื่อตรวจว่าการปรับปรุงนี้มีความหมายทางสถิติหรือเป็นเพียงความบังเอิญ

McNemar's test (χ² = 50.70, p = 7.50 x 10^-13) สนับสนุนความเหนือกว่าของ temporal model เพิ่มเติม ดังแสดงใน Fig. 3 temporal model ทำนายถูกได้มากกว่ามากในกรณีที่ baseline model ล้มเหลว (394 เทียบกับ 217) ความแตกต่างขนาดใหญ่นี้ชี้ถึงการปรับปรุงอย่างมีนัยสำคัญทางสถิติ (p < 0.001) ที่เกิดจาก temporal model

ข้อค้นพบเหล่านี้ยืนยันว่า performance gain ที่สังเกตได้ไม่น่าจะเกิดจากความบังเอิญ ดังนั้นการรวม temporal information จึงให้คุณค่าเชิงทำนายที่มีความหมายเหนือกว่า single-shot clinical records และทำให้ stroke-risk prediction มีความน่าเชื่อถือมากขึ้น

รูปที่ 3: การเปรียบเทียบ McNemar ระหว่าง temporal features (Extract Set 1 - LAST) และ single-shot baseline (Baseline - LAST)

รูปที่ 4: สมรรถนะ G-Mean ของ ANOVA ภายใต้จำนวน features (k) ที่ต่างกัน

### Table II. การเปรียบเทียบสมรรถนะรวมระหว่าง feature sets และวิธีลดมิติ

| Feature Extraction | Feature Set | Method | Number of features/components | Sensitivity | Specificity | G-Mean |
|---|---|---|---:|---:|---:|---:|
| Single shot | Base line (15) LAST | No reduce | 15 | 0.5883 | 0.6362 | 0.6117 |
| Single shot | Base line (15) LAST | F-ANOVA | 6 | 0.6084 | 0.6413 | 0.6241 |
| Single shot | Base line (15) LAST | PCA | 9 | 0.6152 | 0.6431 | 0.6287 |
| Single shot | Base line (15) LAST | F-ANOVA+PCA | 3 | 0.6251 | 0.6197 | 0.6223 |
| Temporal feature | Extract Set 1 (35) MEAN | No reduce | 35 | 0.5873 | 0.6512 | 0.6183 |
| Temporal feature | Extract Set 1 (35) MEAN | F-ANOVA | 30 | 0.6224 | 0.6423 | 0.6322 |
| Temporal feature | Extract Set 1 (35) MEAN | PCA | 35 | 0.5942 | 0.6623 | 0.6274 |
| Temporal feature | Extract Set 1 (35) MEAN | F-ANOVA+PCA | 15 | 0.6283 | 0.6279 | 0.6281 |
| Temporal feature | Extract Set 1 (35) LAST | No reduce | 35 | 0.5943 | 0.6613 | 0.6273 |
| Temporal feature | Extract Set 1 (35) LAST | F-ANOVA | 30 | 0.5954 | 0.6631 | 0.6284 |
| Temporal feature | Extract Set 1 (35) LAST | PCA | 30 | 0.6013 | 0.6614 | 0.6307 |
| Temporal feature | Extract Set 1 (35) LAST | F-ANOVA+PCA | 29 | 0.5878 | 0.6509 | 0.6192 |
| Temporal feature | Extract Set 2 (115) MEAN | No reduce | 115 | 0.5274 | 0.6703 | 0.5943 |
| Temporal feature | Extract Set 2 (115) MEAN | F-ANOVA | 4 | 0.5813 | 0.6364 | 0.6081 |
| Temporal feature | Extract Set 2 (115) MEAN | PCA | 30 | 0.6014 | 0.6203 | 0.6107 |
| Temporal feature | Extract Set 2 (115) MEAN | F-ANOVA+PCA | 2 | 0.6553 | 0.5362 | 0.5928 |
| Temporal feature | Extract Set 2 (115) LAST | No reduce | 115 | 0.5332 | 0.6743 | 0.5997 |
| Temporal feature | Extract Set 2 (115) LAST | F-ANOVA | 20 | 0.6154 | 0.6334 | 0.6241 |
| Temporal feature | Extract Set 2 (115) LAST | PCA | 30 | 0.6153 | 0.6624 | 0.6385 |
| Temporal feature | Extract Set 2 (115) LAST | F-ANOVA+PCA | 19 | 0.6216 | 0.6483 | 0.6348 |
| Temporal feature | Extract Set 3 (121) MEAN | No reduce | 121 | 0.5063 | 0.6842 | 0.5884 |
| Temporal feature | Extract Set 3 (121) MEAN | F-ANOVA | 40 | 0.6084 | 0.6453 | 0.6263 |
| Temporal feature | Extract Set 3 (121) MEAN | PCA | 30 | 0.5743 | 0.6493 | 0.6107 |
| Temporal feature | Extract Set 3 (121) MEAN | F-ANOVA+PCA | 12 | 0.6418 | 0.6214 | 0.6315 |
| Temporal feature | Extract Set 3 (121) LAST | No reduce | 121 | 0.5273 | 0.6842 | 0.6007 |
| Temporal feature | Extract Set 3 (121) LAST | F-ANOVA | 30 | 0.6283 | 0.6454 | 0.6367 |
| Temporal feature | Extract Set 3 (121) LAST | PCA | 50 | 0.5883 | 0.6703 | 0.6279 |
| Temporal feature | Extract Set 3 (121) LAST | F-ANOVA+PCA | 22 | 0.6351 | 0.6415 | 0.6383 |

รูปที่ 5: สมรรถนะ G-Mean ของ PCA ภายใต้จำนวน components (k) ที่ต่างกัน

### B. สมรรถนะของการคัดเลือก features (F-ANOVA)

การวิเคราะห์ dimensionality reduction เริ่มจากการประเมิน supervised feature selection ด้วย ANOVA F-test features ถูกจัดอันดับด้วย F-scores และค่อย ๆ เพิ่ม top-k features เพื่อประเมินการเปลี่ยนแปลงของสมรรถนะ ดังแสดงใน Table II สมรรถนะของโมเดลดีขึ้นเมื่อรวม informative features มากขึ้น และถึงจุดสูงสุดใน configuration Extract Set 3 - LAST (G-Mean = 0.637 ที่ประมาณ 30 features, Fig. 4) อย่างไรก็ตาม การเพิ่ม features หลังจากจุดนี้ไม่ได้ให้ประโยชน์เพิ่มเติม และในบางกรณีลดความเสถียรของโมเดล

### C. สมรรถนะของ PCA

ถัดมา PCA ถูกประเมินในฐานะ unsupervised dimensionality-reduction method PCA ฉาย original feature space ไปยังชุดของ orthogonal components ที่เรียงตามปริมาณ variance explained จำนวน components ถูกเพิ่มทีละระดับ (k = 1 ถึง K) เพื่อวิเคราะห์ trade-off ระหว่าง dimensionality และ predictive performance

ดังแสดงใน Table II PCA ให้สมรรถนะสูงสุดเมื่อใช้ Extract Set 2 - LAST feature set ที่ประมาณ 30 components โดยได้ G-Mean 0.638 แนวโน้มนี้สอดคล้องอย่างใกล้เคียงกับรูปแบบที่พบจาก ANOVA นอกจากนี้ PCA ยังมีประสิทธิภาพในการลด multicollinearity และบีบอัดตัวแปรที่มีความสัมพันธ์สูงให้เป็น latent representations ที่กระชับ (Fig. 5)

### การเปรียบเทียบระหว่าง Single-Shot และ F-ANOVA + PCA Models

เพื่อประเมินประโยชน์ของ temporal information และ dimensionality reduction ผู้วิจัยเปรียบเทียบ F-ANOVA + PCA model ที่เสนอ กับ traditional single-shot baseline โดยใช้ Extract Set 3 (LAST) F-ANOVA + PCA model ซึ่งใช้ top 30 ANOVA features ตามด้วย PCA ได้ G-Mean = 0.6383 สูงกว่า single-shot model ซึ่งได้ G-Mean = 0.611

McNemar's test (Fig. 6) ยืนยันเพิ่มเติมว่ามีความแตกต่างอย่างมีนัยสำคัญระหว่างโมเดลทั้งสอง: single-shot model จำแนกถูก 223 cases ที่ F-ANOVA + PCA model จำแนกผิด ขณะที่โมเดลที่เสนอแก้ไขได้ 286 cases ที่ single-shot approach จำแนกผิด (χ² = 7.55, p = 0.006) ข้อค้นพบเหล่านี้ชี้ว่าการรวม temporal windows เข้ากับ ANOVA-to-PCA dimensionality reduction ให้ความสามารถในการทำนายที่แข็งแรงกว่าการอาศัยการวัดล่าสุดเพียงครั้งเดียวอย่างชัดเจน

### D. การเปรียบเทียบกับงานศึกษาก่อนหน้า

งานศึกษาก่อนหน้าได้รายงาน predictive performance ที่สูงโดยใช้ข้อมูลด้านประชากรศาสตร์ พฤติกรรม และข้อมูลทางคลินิกจำกัด ดังแสดงใน Table III อย่างไรก็ตาม โมเดลที่มีอยู่ส่วนใหญ่พึ่งพา single-shot data ซึ่งใช้เพียงหนึ่งระเบียนต่อผู้ป่วย ทำให้ความสามารถในการจับ longitudinal health dynamics เช่น progressive hypertension, renal decline หรือ lipid fluctuations ถูกจำกัด

งานจำนวนมาก รวมถึงงานของ Wang และคณะ, Emon และคณะ และ Das และคณะ ใช้ข้อมูลด้านประชากรศาสตร์หรือข้อมูล self-reported เป็นหลัก โดยนำ objective laboratory data เข้ามาน้อย แม้ Chowdhury และคณะจะนำ temporal features บางส่วนเข้ามาใช้ แต่แนวทางของพวกเขาไม่ได้ใช้ structured multi-window EHR design หรือ comprehensive physiological tracking

ในทางตรงกันข้าม วิธีของงานนี้ใช้ real-world longitudinal EHR ร่วมกับ integrated temporal features, demographic factors และ laboratory measurements สิ่งนี้ให้การแทน physiological changes over time ที่แม่นยำกว่า และเป็นพื้นฐานที่แข็งแรงกว่าสำหรับ clinical decision-making แม้ raw accuracy จะต่ำกว่าเนื่องจากความซับซ้อนของข้อมูลโรงพยาบาลจริง framework ที่เสนอนี้เติมช่องว่างเชิงวิธีวิทยาที่สำคัญด้วยการ modeling true temporal health trajectories ซึ่งจำเป็นสำหรับ early stroke-risk prediction

รูปที่ 6: การเปรียบเทียบ McNemar ระหว่าง temporal features (Extract Set 1 - LAST) และ single-shot baseline (Baseline - LAST)

### Table III. การเปรียบเทียบ data modalities และ predictive performance ระหว่างงานศึกษาก่อนหน้า

| Study | Single-shot | Temporal features | Demographic Info | Laboratory Measurements | Accuracy | Sensitivity | Specificity |
|---|---|---|---|---|---:|---:|---:|
| Ours (F-ANOVA + PCA) | | / | / | / | 0.641 | 0.635 | 0.641 |
| Wang et al. [3] | / | | / | | 0.958 | 0.984 | 0.933 |
| Emon et al. [4] | / | | / | | 0.970 | 1.000 | 0.900 |
| Das et al. [5] | / | | / | | 0.984 | 0.983 | - |
| Dritsas and Trigka [6] | / | | / | | 0.989 | 0.974 | - |
| Chowdhury et al. [7] | / | / | / | | 0.980 | 0.884 | 0.991 |

## IV. สรุปผล

งานศึกษานี้นำเสนอ temporal-feature framework สำหรับ stroke-risk prediction โดยใช้ real-world longitudinal EHR ซึ่งช่วยแก้ข้อจำกัดสำคัญของ single-shot models ด้วยการจัดโครงสร้าง records ของผู้ป่วยเป็น retrospective windows มาตรฐานสามช่วงและใช้ completeness criteria วิธีนี้สามารถจับ physiological trends ที่มีความหมายซึ่งไม่สามารถสังเกตได้จาก single-timepoint data

ผลลัพธ์แสดงว่า temporal features ปรับปรุง predictive performance เหนือ single-shot baseline อย่างชัดเจน การรวม F-ANOVA และ PCA ยังช่วยเพิ่ม model accuracy โดยได้ G-Mean สูงสุด และ test ยืนยันว่าการปรับปรุงเหล่านี้มีนัยสำคัญทางสถิติ โดยรวมแล้ว ข้อค้นพบเน้นคุณค่าของ temporal health trajectories และ dimensionality reduction ในการ modeling clinical outcomes ที่ซับซ้อน framework ที่เสนอนี้วางรากฐานสำหรับ stroke-risk stratification ที่ทนทานและประยุกต์ใช้ทางคลินิกได้มากขึ้น โดยใช้ routine hospital EHR

## กิตติกรรมประกาศ

งานศึกษานี้ได้รับการสนับสนุนทางการเงินจาก Faculty of Informatics, Burapha University งานนี้ได้รับการสนับสนุนจาก Suranaree University of Technology (SUT), Thailand Science Research and Innovation (TSRI), และ National Science Research and Innovation Fund (NSRF) (NRIIS no.195615)

## เอกสารอ้างอิง

[1] “Cover Story | Stroke: Back to the Basics,” American College of Cardiology. Accessed: Dec. 25, 2025. Available online.

[2] L. Evans, “Improvements in stroke care, awareness and early detection,” Open Access Government. Accessed: Dec. 25, 2025. Available online.

[3] R. Wang, J. Zhang, B. Shan, M. He, and J. Xu, “XGBoost Machine Learning Algorithm for Prediction of Outcome in Aneurysmal Subarachnoid Hemorrhage,” Neuropsychiatric Disease and Treatment, vol. 18, pp. 659-667, Mar. 2022.

[4] M. U. Emon, M. S. Keya, T. I. Meghla, Md. M. Rahman, M. S. A. Mamun, and M. S. Kaiser, “Performance Analysis of Machine Learning Approaches in Stroke Prediction,” ICECA, 2020.

[5] M. C. Das et al., “A comparative study of machine learning approaches for heart stroke prediction,” SmartNets, 2023.

[6] E. Dritsas and M. Trigka, “Stroke Risk Prediction with Machine Learning Techniques,” Sensors, vol. 22, no. 13, 2022.

[7] S. H. Chowdhury, M. Mamun, M. I. Hussain, and Md. S. Iqbal, “Brain Stroke Prediction using Explainable Machine Learning and Time Series Feature Engineering,” ICICT, 2024.

[8] “ICD-10 Version:2019.” Accessed: Dec. 25, 2025. Available online.

[9] S. G. Wannamethee, A. G. Shaper, and I. J. Perry, “Serum Creatinine Concentration and Risk of Cardiovascular Disease,” Stroke, vol. 28, no. 3, pp. 557-563, Mar. 1997.

[10] “Total and High-Density Lipoprotein Cholesterol and Stroke Risk,” Stroke. Accessed: Dec. 25, 2025.

[11] T. S. Bowman et al., “Cholesterol and the Risk of Ischemic Stroke,” Stroke, vol. 34, no. 12, pp. 2930-2934, Dec. 2003.

[12] P. B. Gedeck, Andrew Bruce, Peter, Practical Statistics for Data Scientists, 2nd Edition. Accessed: Dec. 25, 2025.

[13] L. Kabari and B. Nwamae, “Principal Component Analysis (PCA) - An Effective Tool in Machine Learning,” May 2019.
