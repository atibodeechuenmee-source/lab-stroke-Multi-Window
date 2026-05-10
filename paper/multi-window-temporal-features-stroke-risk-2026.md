# Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction

## ข้อมูลอ้างอิง

- ชื่อ paper: Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction
- ผู้แต่ง: Chanon Thansawd, Eri Sato-Shimokawara, Suwanna Rasmequan, Sittisak Saechueng, Yosuke Fukuchi, Waranrach Viriyavit, Peerasak Painprasit, Nobuyuki Nishiuchi
- ปีที่เผยแพร่: 2026
- งานประชุม: 2026 18th International Conference on Knowledge and Smart Technology (KST)
- DOI: `10.1109/KST67832.2026.11431866`
- IEEE: https://ieeexplore.ieee.org/abstract/document/11431866
- PDF ในโปรเจกต์: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- ไฟล์แปลไทยแบบเต็ม: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.th.md`

## สถานะการอ่านล่าสุด

อ่าน PDF รอบล่าสุดครบ 6 หน้าแล้ว และสร้างไฟล์แปลภาษาไทยแบบไม่ย่อไว้ใน `paper/source`

ไฟล์นี้เป็น research note สำหรับใช้เป็น blueprint ของโปรเจกต์ ไม่ใช่คำแปลเต็ม หากต้องการอ่านเนื้อหา paper ตามลำดับหัวข้อเดิมให้ใช้ไฟล์ `.th.md` ใน `paper/source`

## เหตุผลที่เลือก paper นี้

Paper นี้ตรงกับโปรเจกต์ของเราโดยตรง เพราะศึกษาการทำนายความเสี่ยง stroke จาก real-world EHR ในโรงพยาบาลไทย และเน้นปัญหาที่โมเดลแบบ single-shot มองไม่เห็นการเปลี่ยนแปลงสุขภาพตามเวลา เช่น ความดันที่ค่อย ๆ สูงขึ้น ไตเสื่อมลง หรือ lipid profile ผันผวนก่อนเกิด stroke

จุดสำคัญที่นำมาใช้กับโปรเจกต์:

- สร้าง patient-level cohort แทน record-level dataset
- กำหนด `reference date` ชัดเจน
- ลบ post-reference records เพื่อป้องกัน leakage
- สร้าง retrospective temporal windows
- เปรียบเทียบ `single-shot baseline` กับ temporal feature models
- ใช้ `G-Mean` เป็น metric หลักสำหรับข้อมูล class imbalance
- ใช้ McNemar's test เพื่อเทียบ paired predictions

## วัตถุประสงค์ของงานวิจัย

งานวิจัยต้องการทดสอบว่าการใช้ longitudinal EHR เพื่อสร้าง temporal features จากหลายช่วงเวลาก่อน `reference date` ช่วยเพิ่มประสิทธิภาพการทำนายความเสี่ยง stroke ได้ดีกว่าการใช้ clinical record ล่าสุดเพียงครั้งเดียวหรือไม่

ปัญหาหลักที่ paper พยายามแก้คือโมเดล stroke prediction จำนวนมากใช้ข้อมูลแบบ cross-sectional หรือ single-shot ทำให้ไม่เห็น health trajectory ที่ค่อย ๆ เปลี่ยนก่อนเกิด stroke

## Dataset ที่ใช้ใน Paper

- แหล่งข้อมูล: EHR จาก Chokchai Hospital, Thailand
- ช่วงเวลา: ตุลาคม 2014 ถึง มิถุนายน 2024
- จำนวน records เดิม: 245,978 records
- จำนวนผู้ป่วยเดิม: 19,473 คน
- ผู้ป่วยไม่มีประวัติ stroke: 16,696 คน (85.7%)
- ผู้ป่วยมี stroke อย่างน้อย 1 ครั้ง: 2,777 คน (14.3%)
- นิยาม stroke: ICD-10 codes `I60-I68`
- จำนวน attributes เดิม: 45 attributes
- ตัวแปร clinical ที่เลือกใช้: 16 ตัวแปร

หลังใช้ temporal alignment และ completeness criteria เหลือ final dataset:

- ผู้ป่วยทั้งหมด: 3,976 คน
- Stroke cases: 148 คน
- Non-stroke cases: 3,828 คน

ข้อมูลสุดท้ายยังมี class imbalance สูงมาก จึงไม่ควรใช้ accuracy เป็น metric หลักเพียงอย่างเดียว

## Target / Outcome

Outcome คือ binary classification เพื่อทำนายว่าผู้ป่วยเป็น stroke หรือ non-stroke

กติกา reference date:

- Stroke patient: ใช้ first stroke event เป็น `reference date`
- Non-stroke patient: ใช้ last clinical visit เป็น `reference date`
- ลบ records หลัง `reference date` ทั้งหมดเพื่อกัน post-event leakage

แนวคิดนี้ตรงกับ pipeline ของเรา และเป็นเหตุผลที่ Stage 02 ของโปรเจกต์ต้องทำ target/cohort construction ก่อน feature engineering

## Temporal Window Design

Paper สร้าง retrospective observation windows 3 ช่วง:

- FIRST window: 21 ถึง 9 เดือนก่อน reference date
- MID window: 18 ถึง 6 เดือนก่อน reference date
- LAST window: 15 ถึง 3 เดือนก่อน reference date

ทั้ง stroke และ non-stroke patients ใช้โครงสร้าง window เดียวกัน โดยเทียบกับ `reference date` ของแต่ละคน

จากภาพ temporal-window design ใน paper ช่วง FIRST/MID/LAST เป็น overlapping windows ไม่ใช่ช่วงที่แยกกันเด็ดขาด ตัวอย่างเช่น record ที่อยู่ 12 เดือนก่อน reference date จะอยู่ใน FIRST, MID และ LAST พร้อมกัน ดังนั้น implementation ที่ตรง paper ควรเก็บ window membership แบบ long format หรือ multi-hot flags เพื่อให้ record เดียว contribute ได้หลาย windows

ข้อสังเกตต่อโปรเจกต์: ถ้าโค้ดใช้ `window` เป็น label เดียวแบบ exclusive จะทำให้ records ในช่วง overlap ถูกใช้ใน window เดียวเท่านั้น ซึ่งยังไม่ตรงกับภาพใน paper และควรแก้ Stage 02/05 ต่อ

Completeness criteria:

- แต่ละ patient ต้องมีอย่างน้อย 1 visit ในทุก window
- Core clinical variables ที่จำเป็นต้องมีครบในทุก window

ข้อดีคือ temporal features เปรียบเทียบกันได้ระหว่างผู้ป่วย ข้อเสียคือ sample size ลดลงมาก โดยเฉพาะเมื่อ EHR จริง sparse หรือ visit ไม่สม่ำเสมอ

## ตัวแปรสำคัญ

ตัวแปรที่ paper ใช้หรืออ้างถึงในการสร้าง features:

- Age
- Sex / gender
- Systolic blood pressure (BPS)
- Diastolic blood pressure (BPD)
- HDL
- LDL
- Fasting blood sugar (FBS)
- BMI
- eGFR
- Creatinine
- Total cholesterol
- Triglycerides
- Atrial fibrillation (AF)
- Smoking status
- Alcohol drinking status
- Diabetes
- Hypertension
- Heart disease
- Statin use
- Antihypertensive use
- TC:HDL ratio
- Principal diagnosis
- Comorbidity diagnosis
- Dispensed drugs

Derived biomarker:

```text
TC:HDL = Total Cholesterol / HDL
```

## Feature Extraction

Paper แบ่ง feature sets เป็น 3 ระดับ

### Extract Set 1

- จำนวน features: 35
- เป็น core demographic และ clinical variables
- ใช้ numerical variables 10 ตัวใน 3 temporal windows
- รวม categorical features 5 ตัว

### Extract Set 2

- จำนวน features: 115
- ขยายจาก Set 1 ด้วย statistical และ temporal descriptors
- ใช้ descriptors เช่น mean, minimum, maximum, standard deviation, first value, last value, delta change, slope of change, cross-window differences และ measurement count differences

สมการ temporal features หลัก:

```text
Delta(X) = X_LAST - X_FIRST
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST)
```

### Extract Set 3

- จำนวน features: 121
- ขยายจาก Set 2 โดยเพิ่ม risk factors อีก 6 ตัว
- Risk factors คือ diabetes, hypertension, heart disease, statin use, antihypertensive use และ TC:HDL ratio

## Feature Selection และ Dimensionality Reduction

Paper เปรียบเทียบ 3 วิธี:

- ANOVA F-test
- PCA
- ANOVA F-test ตามด้วย PCA

ANOVA F-test:

- ใช้จัดอันดับ numerical features ตาม discriminative power
- ใช้ forward top-k strategy เช่น k = 5, 10, 15, ...
- เลือก k ที่ให้ G-Mean สูงสุดภายใต้ LOOCV
- ทำแยกสำหรับ Extract Set 1/2/3

PCA:

- Standardize numerical features ก่อนทำ PCA
- ทดลองจำนวน components หลายค่า
- เลือกจำนวน components จาก G-Mean ภายใต้ LOOCV
- ช่วยลด redundancy และ multicollinearity แต่ลด interpretability ของ original features

ANOVA + PCA:

- เลือก top-k features ด้วย ANOVA ก่อน
- จากนั้นทำ PCA บน selected features
- ใช้ Logistic Regression ประเมิน performance

## Model

งานนี้ใช้ Logistic Regression เป็น binary classifier:

```text
class_weight = "balanced"
```

เหตุผลที่เลือก:

- ตีความได้ง่าย
- มีประสิทธิภาพพอสำหรับ clinical decision support
- เหมาะเป็น baseline ที่อธิบายได้
- ลด bias ต่อ majority class ด้วย `class_weight="balanced"`

Validation ใช้ Leave-One-Out Cross-Validation (LOOCV) โดย hold out ผู้ป่วยทีละคนเป็น test case เพื่อรักษา patient-level independence และลดความเสี่ยง data leakage

## Evaluation Metrics

Metrics หลัก:

- Sensitivity
- Specificity
- G-Mean
- McNemar's test

G-Mean:

```text
G-Mean = sqrt(Sensitivity * Specificity)
```

เหตุผลที่เน้น G-Mean คือ dataset มี class imbalance สูงมาก หากใช้ accuracy อย่างเดียว โมเดลอาจดูดีเพราะทำนาย majority class ได้ดี แต่ทำงานแย่กับ stroke class

McNemar's test ใช้เทียบ paired classifiers โดยดู disagreement cases ระหว่างโมเดลสองตัว เช่น baseline ทำนายถูกแต่ temporal model ทำนายผิด และ temporal model ทำนายถูกแต่ baseline ทำนายผิด

## ผลลัพธ์สำคัญ

Temporal model ทำได้ดีกว่า single-shot baseline

ตัวเลขหลักจาก Table II:

- Single-shot baseline, LAST, no reduction: G-Mean 0.6117
- Single-shot baseline, LAST, PCA: G-Mean 0.6287
- Extract Set 1, LAST, no reduction: G-Mean 0.6273
- Extract Set 1, LAST, PCA: G-Mean 0.6307
- Extract Set 2, LAST, PCA: G-Mean 0.6385
- Extract Set 3, LAST, F-ANOVA: G-Mean 0.6367
- Extract Set 3, LAST, F-ANOVA + PCA: G-Mean 0.6383

ผลที่ดีที่สุดอยู่ประมาณ G-Mean 0.638

McNemar's test:

- Temporal features เทียบกับ single-shot baseline: chi-square = 50.70, p = 7.50 x 10^-13
- F-ANOVA + PCA เทียบกับ single-shot baseline: chi-square = 7.55, p = 0.006

ตีความได้ว่า temporal information มี predictive value เพิ่มจากการใช้ visit ล่าสุดเพียงครั้งเดียวอย่างมีนัยสำคัญ

## การเทียบกับงานก่อนหน้า

Paper ชี้ว่างานก่อนหน้าหลายชิ้นรายงาน accuracy สูงมาก แต่ส่วนใหญ่ใช้ single-shot data หรือใช้ demographic/self-reported attributes เป็นหลัก จึงอาจไม่ได้จับ physiological trajectory จริงจาก EHR

จุดต่างของ paper นี้:

- ใช้ real-world longitudinal EHR
- ใช้ multi-window temporal representation
- รวม laboratory measurements
- เน้นการเปรียบเทียบกับ single-shot baseline
- ใช้ metrics ที่เหมาะกับ class imbalance

แม้ accuracy/G-Mean ไม่สูงเท่างานบางชิ้น แต่ paper ให้ความสำคัญกับความสมจริงของข้อมูลโรงพยาบาลและการจับ temporal health trajectories

## ข้อจำกัดของงานวิจัย

- หลังใช้ completeness criteria เหลือ stroke cases เพียง 148 ราย
- ใช้ข้อมูลจากโรงพยาบาลเดียว จึงยังต้องการ external validation
- เกณฑ์ต้องมีข้อมูลครบทุก window อาจ exclude ผู้ป่วยจำนวนมาก
- G-Mean สูงสุดประมาณ 0.638 ยังเป็น performance ระดับปานกลาง ไม่ใช่ระดับพร้อม deploy ทันที
- Logistic Regression จับ nonlinear temporal interaction ได้จำกัด
- PCA ช่วยลดมิติ แต่ลด interpretability ของ original features

## สิ่งที่นำมาใช้กับโปรเจกต์ของเรา

ควรใช้ paper นี้เป็น blueprint สำหรับ:

- Stage 02: target/cohort/reference date
- Stage 03: cleaning และ leakage prevention
- Stage 05: temporal feature engineering
- Stage 06: interpretable baseline modeling
- Stage 07: ANOVA/PCA/ANOVA+PCA
- Stage 08: G-Mean และ McNemar validation

แนวคิดที่ต้องรักษา:

- สร้าง patient-level cohort
- ใช้ ICD-10 `I60-I68`
- ลบ post-reference records
- สร้าง temporal windows FIRST/MID/LAST
- รองรับ overlapping window membership ตามภาพใน paper
- เก็บ single-shot baseline เป็น comparator เสมอ
- ใช้ metrics สำหรับ class imbalance
- รายงาน skipped cases เมื่อ temporal completeness ทำให้ class distribution ไม่พอ

## เทียบกับข้อมูลโปรเจกต์ปัจจุบัน

ข้อมูลของเราเมื่อใช้ strict paper-style windows:

- raw patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13

ความต่างสำคัญจาก paper:

- Paper เหลือ final cohort 3,976 patients
- ของเราเหลือ temporal-complete patients เพียง 13 ราย
- ทำให้ temporal models ใน Stage 06-08 ยัง train/evaluate ไม่ได้จริงตาม paper

ข้อเสนอสำหรับงานถัดไป:

- ทำ sensitivity analysis ด้วย alternative windows เช่น 90/180 วัน
- ทดลองลดความเข้มของ completeness criteria บางส่วน
- ตรวจ missingness ต่อ window เพื่อหาสาเหตุที่ temporal-complete cohort หายไปมาก
- ยังเก็บ paper windows 21-9, 18-6, 15-3 เดือนเป็น baseline หลัก

## หมายเหตุเพิ่มเติม

Paper นี้มีประโยชน์มากกว่า related work ทั่วไป เพราะใช้บริบท EHR จริงในโรงพยาบาลไทย และมีปัญหาใกล้กับข้อมูลของโปรเจกต์เราโดยตรง

จุดที่ต้องตรวจสอบต่อ:

- ข้อมูลของเรามี visit เพียงพอในแต่ละ temporal window หรือไม่
- ตัวแปร core clinical ครบทุก window หรือขาดเฉพาะบาง lab
- การใช้ completeness criteria แบบ paper ทำให้เกิด selection bias หรือไม่
- ควรเพิ่ม model ที่จับ nonlinear pattern ได้ เช่น Random Forest หรือ XGBoost หรือไม่ โดยยังคง Logistic Regression เป็น interpretable baseline
