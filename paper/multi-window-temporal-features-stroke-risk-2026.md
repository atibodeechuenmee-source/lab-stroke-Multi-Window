# Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction

## ข้อมูลอ้างอิง

- ชื่อ paper: Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction
- ผู้แต่ง: Chanon Thansawd, Eri Sato-Shimokawara, Suwanna Rasmequan, Sittisak Saechueng, Yosuke Fukuchi, Waranrach Viriyavit, Peerasak Painprasit, Nobuyuki Nishiuchi
- ปีที่เผยแพร่: 2026
- งานประชุม: 2026 18th International Conference on Knowledge and Smart Technology (KST)
- DOI: 10.1109/KST67832.2026.11431866
- URL: https://ieeexplore.ieee.org/abstract/document/11431866
- ไฟล์ PDF ในโปรเจกต์: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`

## ลิงก์อ้างอิง

- Paper: https://ieeexplore.ieee.org/abstract/document/11431866
- DOI: https://doi.org/10.1109/KST67832.2026.11431866
- Dataset/Code ถ้ามี: ไม่พบการเผยแพร่ dataset หรือ source code ใน paper

## เหตุผลที่เลือก paper นี้

Paper นี้ตรงกับโปรเจกต์ของเราอย่างมาก เพราะเป็นงานทำนายความเสี่ยง stroke จากข้อมูล EHR จริงของโรงพยาบาลในประเทศไทย และไม่ได้ใช้ข้อมูลแบบ single-shot เพียง record ล่าสุดเท่านั้น แต่สร้าง temporal features จากประวัติย้อนหลังหลายช่วงเวลาเพื่อจับแนวโน้มสุขภาพก่อนเกิด stroke

จุดที่มีประโยชน์มากคือ paper เสนอวิธีจัดข้อมูลผู้ป่วยให้เป็น patient-level cohort, กำหนด reference date, ตัดข้อมูลหลัง event เพื่อกัน data leakage, สร้าง retrospective windows และเปรียบเทียบ baseline แบบ single-shot กับ temporal model โดยใช้ metric ที่เหมาะกับ class imbalance เช่น G-Mean

## วัตถุประสงค์ของงานวิจัย

งานวิจัยนี้ต้องการทดสอบว่าการนำข้อมูล longitudinal EHR มาสร้าง temporal features หลายช่วงเวลาสามารถเพิ่มประสิทธิภาพการทำนายความเสี่ยง stroke ได้ดีกว่าการใช้ข้อมูล clinical record ล่าสุดเพียงครั้งเดียวหรือไม่

ปัญหาหลักที่ paper พยายามแก้คือ model ทำนาย stroke จำนวนมากใช้ข้อมูลแบบ cross-sectional หรือ single-shot ทำให้มองไม่เห็นการเปลี่ยนแปลงทางสุขภาพที่ค่อย ๆ เกิดขึ้นก่อน stroke เช่น ความดันเพิ่มขึ้น ค่าไตลดลง หรือค่า lipid เปลี่ยนแปลงตามเวลา

## Dataset ที่ใช้

- แหล่งข้อมูล: Electronic Health Records จาก Chokchai Hospital, Thailand
- ช่วงเวลา: ตุลาคม 2014 ถึง มิถุนายน 2024
- จำนวน records เดิม: 245,978 records
- จำนวนผู้ป่วยเดิม: 19,473 คน
- ผู้ป่วยไม่มีประวัติ stroke: 16,696 คน หรือ 85.7%
- ผู้ป่วยมี stroke อย่างน้อย 1 ครั้ง: 2,777 คน หรือ 14.3%
- นิยาม stroke: ICD-10 codes `I60-I68`
- จำนวน attributes เดิม: 45 attributes
- จำนวนตัวแปร clinical ที่เลือกใช้: 16 ตัวแปร

หลังจาก temporal alignment และ completeness filtering เหลือ cohort สุดท้าย:

- จำนวนผู้ป่วยทั้งหมด: 3,976 คน
- Stroke cases: 148 คน
- Non-stroke cases: 3,828 คน

ข้อมูลสุดท้ายมี class imbalance สูงมาก จึงต้องใช้วิธีประเมินผลที่ไม่พึ่ง accuracy เพียงอย่างเดียว

## Target / Outcome

Outcome คือ binary classification เพื่อทำนายว่าผู้ป่วยจะเป็น stroke หรือ non-stroke

สำหรับผู้ป่วย stroke ใช้ first stroke event เป็น reference date ส่วนผู้ป่วย non-stroke ใช้ last clinical visit เป็น reference date จากนั้นลบ records หลัง reference date ออกทั้งหมดเพื่อป้องกัน post-event leakage

ในแง่โปรเจกต์ของเรา paper นี้ใช้ target ใกล้เคียงกับแนวคิด patient-level stroke occurrence โดยอ้างอิง ICD-10 `I60-I68` ซึ่งเป็นกลุ่ม cerebrovascular diseases ที่เกี่ยวข้องกับ stroke

## Temporal Window Design

Paper สร้าง retrospective observation windows 3 ช่วง:

- FIRST window: 21 ถึง 9 เดือนก่อน reference date
- MID window: 18 ถึง 6 เดือนก่อน reference date
- LAST window: 15 ถึง 3 เดือนก่อน reference date

ทั้ง stroke และ non-stroke patients ใช้โครงสร้าง window เดียวกัน โดยเทียบกับ reference date ของแต่ละคน

เกณฑ์ completeness ที่ใช้:

- แต่ละ patient ต้องมีอย่างน้อย 1 visit ในทุก window
- core clinical variables ต้องมีครบในทุก window

เกณฑ์นี้ช่วยให้ temporal features เปรียบเทียบกันได้ระหว่างผู้ป่วย แต่ทำให้จำนวน sample ลดลงมาก

## Features สำคัญ

ตัวแปรสำคัญที่ใช้ประกอบด้วย:

- Age
- Sex
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
- Atrial fibrillation
- Smoking status
- Alcohol drinking status
- Diabetes
- Hypertension
- Heart disease
- Statin use
- Antihypertensive use
- TC:HDL ratio

TC:HDL ratio คำนวณจาก:

```text
TC:HDL = Total Cholesterol / HDL
```

## Feature Extraction

Paper แบ่ง feature sets เป็น 3 ระดับ:

### Extract Set 1

- จำนวน features: 35
- เป็น core demographic และ clinical variables
- ใช้ numerical variables 10 ตัวใน 3 temporal windows
- รวม categorical features 5 ตัว

### Extract Set 2

- จำนวน features: 115
- เพิ่ม statistical และ temporal descriptors จาก numerical variables
- descriptors สำคัญ เช่น mean, minimum, maximum, standard deviation, first value, last value, delta change, slope of change, cross-window differences และ measurement count differences

สมการ temporal features หลัก:

```text
Delta(X) = X_LAST - X_FIRST
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST)
```

### Extract Set 3

- จำนวน features: 121
- เพิ่ม risk factors อีก 6 ตัวจาก Extract Set 2
- risk factors คือ diabetes, hypertension, heart disease, statin use, antihypertensive use และ TC:HDL ratio

## Method / Model

งานนี้ใช้ Logistic Regression เป็น binary classifier โดยกำหนด class weight เพื่อรับมือ class imbalance:

```text
class_weight = "balanced"
```

เหตุผลที่เลือก Logistic Regression คือ interpretability, efficiency และเหมาะกับ clinical decision support ที่ต้องการอธิบายผลได้

การ validation ใช้ Leave-One-Out Cross-Validation (LOOCV) โดย hold out ผู้ป่วยทีละคนเป็น test case เพื่อรักษา patient-level independence และลดโอกาส data leakage

## Feature Selection / Dimensionality Reduction

Paper เปรียบเทียบ 3 วิธี:

- ANOVA F-test
- Principal Component Analysis (PCA)
- ANOVA F-test ตามด้วย PCA

ANOVA F-test ใช้จัดอันดับ features ตาม discriminative power แล้วเลือก top-k features โดยหา k ที่ให้ G-Mean ดีที่สุด

PCA ใช้ลด redundancy และ multicollinearity ของ temporal features โดยแปลง features เป็น orthogonal components แล้วเลือกจำนวน components ที่เหมาะสมจาก LOOCV

## Evaluation Metrics

Metrics ที่ใช้:

- Sensitivity
- Specificity
- G-Mean
- McNemar's test สำหรับเปรียบเทียบ paired classifiers

G-Mean เป็น metric หลัก:

```text
G-Mean = sqrt(Sensitivity * Specificity)
```

G-Mean เหมาะกับข้อมูล imbalance เพราะบังคับให้ model ต้องทำได้ดีทั้งกลุ่ม stroke และ non-stroke ไม่ใช่ทาย majority class ได้ดีอย่างเดียว

## ผลลัพธ์สำคัญ

Temporal model ทำได้ดีกว่า single-shot baseline

- Single-shot baseline ใช้ clinical record ล่าสุดเพียงครั้งเดียว
- Single-shot baseline มี G-Mean ประมาณ 0.612
- Temporal model แบบ Extract Set 1, LAST, no reduction มี G-Mean ประมาณ 0.627
- Extract Set 2, LAST, PCA ได้ G-Mean ประมาณ 0.6385
- Extract Set 3, LAST, F-ANOVA ได้ G-Mean ประมาณ 0.6367
- Extract Set 3, LAST, F-ANOVA + PCA ได้ G-Mean ประมาณ 0.6383

ผลที่ดีที่สุดอยู่ประมาณ G-Mean 0.638

McNemar's test พบว่า temporal model ดีกว่า single-shot baseline อย่างมีนัยสำคัญ เช่น:

- Temporal features เทียบกับ single-shot baseline: chi-square = 50.70, p = 7.50e-13
- F-ANOVA + PCA เทียบกับ single-shot baseline: chi-square = 7.55, p = 0.006

ผลลัพธ์ตีความได้ว่า temporal information มี predictive value เพิ่มจากการใช้ข้อมูล visit ล่าสุดเพียงครั้งเดียว

## ข้อจำกัดของงานวิจัย

- หลังใช้ completeness criteria เหลือ stroke cases เพียง 148 คน
- ข้อมูลมาจากโรงพยาบาลเดียว จึงยังต้องการ external validation
- เกณฑ์ต้องมีข้อมูลครบทุก window อาจทำให้ exclude ผู้ป่วยจำนวนมาก และอาจไม่สะท้อนการใช้งานจริงกับ EHR ที่ sparse มาก
- G-Mean สูงสุดประมาณ 0.638 ยังถือว่าปานกลาง ไม่ใช่ performance ระดับพร้อมใช้งานจริงทันที
- Logistic Regression อาจจับ nonlinear temporal interaction ได้จำกัด
- PCA ช่วยลดมิติ แต่ทำให้ interpretability ของ features ลดลง

## สิ่งที่นำมาใช้กับโปรเจกต์ของเราได้

แนวคิดที่ควรนำมาใช้:

- สร้าง patient-level cohort แทน record-level dataset
- กำหนด reference date ให้ชัดเจน
- ลบ post-reference records เพื่อกัน data leakage
- สร้าง retrospective windows ก่อน stroke event หรือก่อน last visit
- เปรียบเทียบ single-shot baseline กับ temporal feature model
- สร้าง features เช่น mean, min, max, standard deviation, first, last, delta และ slope
- ใช้ G-Mean, sensitivity และ specificity เป็น metrics หลัก เพราะข้อมูล stroke imbalance
- ใช้ McNemar's test เพื่อเปรียบเทียบ model แบบ paired prediction
- ใช้ Logistic Regression เป็น interpretable baseline ก่อนต่อยอดไป Random Forest หรือ XGBoost

สำหรับ pipeline ของเรา paper นี้เหมาะใช้เป็น blueprint ของ temporal feature engineering โดยเฉพาะขั้นตอน target/cohort construction, leakage prevention และ patient-level validation

## หมายเหตุเพิ่มเติม

Paper นี้มีประโยชน์มากกว่าแค่เป็น related work เพราะเป็นงานที่ใช้ข้อมูล EHR จริงในบริบทโรงพยาบาลไทย และมีปัญหาใกล้กับข้อมูลของเราโดยตรง

ประเด็นที่ควรตรวจสอบต่อเมื่อทำงานของเรา:

- เรามี visit เพียงพอในแต่ละ temporal window หรือไม่
- ถ้าใช้ completeness criteria เข้มแบบ paper นี้ sample จะลดลงมากแค่ไหน
- ควรใช้ window เดียวกัน 21-9, 18-6, 15-3 เดือน หรือปรับเป็น 90 วัน / 180 วัน ตาม target ของเรา
- ควรทำ sensitivity analysis เทียบหลาย window definitions
- ควรเพิ่ม model ที่จับ nonlinear pattern ได้ เช่น XGBoost แต่ยังเก็บ Logistic Regression เป็น baseline ที่อธิบายง่าย
