# ตรวจเช็คความเหมือนกับงานวิจัย Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction

## Reference

- Paper PDF: `paper/source/Multi-Window_Timeframe_Temporal_Features_for_Stroke-Risk_Prediction.pdf`
- Paper note: `paper/multi-window-temporal-features-stroke-risk-2026.md`
- IEEE ref: https://ieeexplore.ieee.org/abstract/document/11431866

## สรุปสั้น

งานของเราเดินตามแนวคิดหลักของ paper แล้วในระดับ pipeline design และ implementation ช่วง Stage 01-06 ได้แก่ raw audit, target/cohort, cleaning, EDA, feature engineering และ modeling baseline

ส่วนที่เหมือน paper มาก:

- ใช้ข้อมูล EHR แบบ longitudinal
- สร้าง patient-level cohort
- กำหนด `reference date`
- ตัด post-reference records เพื่อกัน data leakage
- ใช้ ICD-10 `I60-I68` เป็น stroke definition
- สร้าง temporal windows `FIRST`, `MID`, `LAST`
- สร้าง single-shot baseline จาก latest pre-reference record
- สร้าง temporal feature sets แบบ hierarchical
- ใช้ Logistic Regression พร้อม `class_weight="balanced"`
- ใช้ sensitivity, specificity และ G-Mean เป็น metrics หลักใน modeling

ส่วนที่ยังไม่เหมือน paper หรือยังไม่สมบูรณ์:

- temporal-complete patients ในข้อมูลเรามีเพียง 13 คน และมี stroke positive เพียง 1 รายใน temporal feature tables ทำให้ train temporal models ไม่ได้
- Stage 06 ใช้ `StratifiedKFold_5` สำหรับ baseline แทน LOOCV เพราะ baseline มี 13,635 patients และ LOOCV มี cost สูง
- Stage 07 ANOVA F-test, PCA และ ANOVA+PCA ยังไม่ได้ implement เป็น module แยก
- Stage 08 validation และ McNemar's test ยังไม่ได้ implement เป็น module แยก
- จำนวน features ของ Extract Set 2/3 ใน implementation มากกว่า paper เพราะเราสร้าง descriptors เพิ่มหลายชนิดและเก็บ feature แบบละเอียดกว่า
- ยังไม่ได้ทำ comparison temporal model vs single-shot baseline เพราะ temporal models ถูก skip

## Alignment Checklist

| Paper method | งานของเรา | สถานะ | หลักฐาน / หมายเหตุ |
|---|---|---|---|
| ใช้ real-world longitudinal EHR | ใช้ raw Excel จาก `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx` | เหมือน | Stage 01 อ่าน raw EHR 218,772 rows, 13,635 patients |
| ใช้ patient-level cohort | มี `src/target_cohort.py` | เหมือน | สร้าง `patient_level_cohort.csv` จาก Stage 02 |
| Stroke definition ด้วย ICD-10 `I60-I68` | ใช้ regex ตรวจ `I60-I68` ใน diagnosis fields | เหมือน | Stage 01 พบ stroke ICD hits 3,950 records; Stage 02 ได้ stroke patients 969 |
| Stroke reference date = first stroke event | ทำใน `src/target_cohort.py` | เหมือน | quality check: `stroke_reference_is_first_stroke_date = true` |
| Non-stroke reference date = last visit | ทำใน `src/target_cohort.py` | เหมือน | quality check: `nonstroke_reference_is_last_visit_date = true` |
| Remove post-event/post-reference records | ตัด records หลัง reference date | เหมือน | Stage 02/03/05 checks: `no_post_reference_records = true` |
| Temporal windows FIRST/MID/LAST | ใช้ windows ตาม paper | เหมือน | FIRST 21-9 เดือน, MID 18-6 เดือน, LAST 15-3 เดือน |
| ต้องมีอย่างน้อย 1 visit ทุก window | ตรวจ temporal completeness | เหมือน | `temporal_complete_patients = 13` |
| Core clinical variables ต้องครบทุก window | ตรวจ core numeric coverage ทุก window | เหมือนในหลักการ | implementation ใช้ core numerical variables 10 ตัว |
| Single-shot baseline จาก latest pre-reference record | มี `single_shot_features.csv` | เหมือน | Stage 05 ได้ 13,635 rows |
| Extract Set 1 | มี `extract_set_1_features.csv` | ใกล้เคียง | ได้ 13 rows x 36 columns; ใกล้กับ paper 35 features |
| Extract Set 2 | มี `extract_set_2_features.csv` | บางส่วนเหมือน แต่จำนวน features ต่าง | ได้ 13 rows x 266 columns; paper ระบุ 115 features |
| Extract Set 3 | มี `extract_set_3_features.csv` | บางส่วนเหมือน แต่จำนวน features ต่าง | ได้ 13 rows x 272 columns; paper ระบุ 121 features |
| TC:HDL ratio | รองรับ `tc_hdl_ratio` และคำนวณถ้ายังไม่มี | เหมือน | Stage 05 ป้องกันหาร HDL ด้วยศูนย์ |
| Statistical descriptors: mean/min/max/std/first/last | Implement แล้ว | เหมือน | อยู่ใน `src/feature_engineering.py` |
| Temporal descriptors: delta/slope/cross-window differences/count differences | Implement แล้ว | เหมือนในหลักการ | สร้าง delta, slope, min/max/count diff LAST-FIRST |
| Logistic Regression | ใช้ Logistic Regression | เหมือน | `src/modeling.py` |
| `class_weight="balanced"` | ใช้แล้ว | เหมือน | `src/modeling.py` |
| LOOCV | ใช้เฉพาะ table ขนาดเล็ก, baseline ใช้ StratifiedKFold | ต่างบางส่วน | implementation เลือกตามขนาดข้อมูลเพื่อให้รันได้จริง |
| Sensitivity, specificity, G-Mean | คำนวณแล้วใน Stage 06 | เหมือน | baseline sensitivity 0.9288, specificity 0.9203, G-Mean 0.9246 |
| McNemar's test | ยังไม่ได้ implement ใน Stage 08 | ยังไม่ครบ | มี helper ใน `src/temporal_pipeline.py` แต่ยังไม่แยก stage validation |
| ANOVA F-test | ยังไม่ได้ implement Stage 07 | ยังไม่ครบ | ยังไม่มี `src/feature_importance.py` ใหม่ |
| PCA | ยังไม่ได้ implement Stage 07 | ยังไม่ครบ | ยังไม่มี module PCA/ANOVA+PCA |
| Compare temporal model vs single-shot baseline | ยังทำไม่ได้ | ยังไม่ครบ | temporal sets มี positive class แค่ 1 ราย จึงถูก skip |

## ผลลัพธ์ปัจจุบันของเรา

### Stage 01 Raw Data

- raw rows: 218,772
- columns: 30
- patients: 13,635
- required fields available: 29
- required fields missing: 0
- stroke ICD `I60-I68` record hits: 3,950

เทียบ paper:

- Paper ใช้ 245,978 records จาก 19,473 patients
- ของเรามี records/patients น้อยกว่า paper แต่เป็นโครงข้อมูลเดียวกันหรือใกล้เคียงมาก

### Stage 02 Target and Cohort

- patients: 13,635
- stroke patients: 969
- non-stroke patients: 12,666
- pre-reference records: 194,231
- temporal-complete patients: 13
- no post-reference records: true

เทียบ paper:

- Paper หลัง completeness filtering เหลือ 3,976 patients, stroke 148, non-stroke 3,828
- ของเราใช้ strict criteria แล้วเหลือเพียง 13 temporal-complete patients ซึ่งน้อยกว่ามาก
- จุดนี้ทำให้ขั้น modeling temporal ยังไม่สามารถเทียบกับ paper ได้จริง

### Stage 03 Data Cleaning

- rows before cleaning: 194,231
- rows after cleaning: 194,231
- duplicate rows removed: 0
- direct/quasi identifier dropped: `ตำบล`
- no post-reference records: true

เทียบ paper:

- Paper ทำ de-identification, date/unit harmonization, implausible value handling, binary encoding และ ICD normalization
- งานเราทำครบในหลักการ
- จุดที่ควรระวังคือ `smoke` และ `drinking` มี code นอก `{0,1}` จำนวนมาก จึงถูก set missing ตาม rule ปัจจุบัน อาจต้องกลับไปยืนยัน data dictionary

### Stage 04 EDA

- records: 194,231
- patients: 13,635
- stroke prevalence: 0.0711
- temporal-complete patients: 13
- high-missing variables >= 50%: 9
- leakage audit passed: true

เทียบ paper:

- Paper เน้นปัญหา irregular/incomplete real-world EHR
- EDA ของเรายืนยันว่าข้อมูลมีปัญหา sparse temporal coverage มากกว่าที่ paper เหลือใช้จริง

### Stage 05 Feature Engineering

- single-shot rows: 13,635
- Extract Set 1: 13 rows x 36 columns
- Extract Set 2: 13 rows x 266 columns
- Extract Set 3: 13 rows x 272 columns
- excluded patients: 13,622
- no post-reference records: true

เทียบ paper:

- โครง feature set เหมือน paper แต่จำนวน features ยังต่าง
- Paper ระบุ Set 1 = 35, Set 2 = 115, Set 3 = 121
- ของเรา Set 1 ใกล้เคียง แต่ Set 2/3 สูงกว่า เพราะสร้าง descriptors เพิ่มละเอียดกว่า paper
- หากต้อง replicate paper ให้ตรง ควรจำกัด descriptors ให้เท่าที่ paper นิยามจริง

### Stage 06 Modeling

- models seen: single_shot, extract_set_1, extract_set_2, extract_set_3
- models completed: 1
- models skipped: 3
- best model: single_shot
- best G-Mean: 0.9246

รายละเอียด baseline:

- `single_shot` completed ด้วย `StratifiedKFold_5`
- sensitivity = 0.9288
- specificity = 0.9203
- ROC-AUC = 0.9679

รายละเอียด temporal models:

- `extract_set_1`, `extract_set_2`, `extract_set_3` ถูก skip
- เหตุผล: temporal-complete set มี positive class เพียง 1 ราย (`not_run_min_class_lt_2`)

เทียบ paper:

- Paper สามารถ train temporal models และรายงาน G-Mean สูงสุดประมาณ 0.638
- งานเรายังไม่สามารถเทียบผล temporal vs single-shot ได้ เพราะ temporal cohort เล็กเกินและมี positive class น้อยเกินไป
- baseline ของเราสูงกว่ามากผิดธรรมชาติเมื่อเทียบ paper จึงควรตรวจ leakage/definition เพิ่ม แม้ pre-reference check จะผ่านแล้ว

## จุดที่เหมือน Paper แล้ว

1. ใช้แนวคิด longitudinal EHR และ patient-level modeling
2. ใช้ ICD-10 `I60-I68` เป็น stroke event definition
3. ใช้ first stroke event / last visit เป็น reference date
4. ตัดข้อมูลหลัง reference date เพื่อกัน leakage
5. ใช้ temporal windows FIRST/MID/LAST ตาม paper
6. ใช้ strict completeness criteria ตาม paper
7. สร้าง single-shot baseline
8. สร้าง temporal feature sets แบบ hierarchical
9. คำนวณ `TC:HDL`
10. สร้าง statistical/temporal descriptors
11. ใช้ Logistic Regression with balanced class weight
12. ใช้ G-Mean ร่วมกับ sensitivity/specificity

## จุดที่ยังต่างจาก Paper

1. Paper เหลือ temporal cohort 3,976 patients แต่ของเราเหลือ 13 patients
2. Paper มี stroke cases หลัง filtering 148 ราย แต่ของเรา temporal-complete มี positive class เพียง 1 ราย
3. Paper ใช้ LOOCV เป็นหลัก ส่วนของเราใช้ stratified CV สำหรับ baseline เพื่อให้รันได้จริง
4. Paper รายงาน temporal model performance ได้ แต่ของเรายัง train temporal models ไม่ได้
5. Paper ใช้ ANOVA F-test/PCA/ANOVA+PCA แต่เรายังไม่ได้ implement Stage 07
6. Paper ใช้ McNemar's test เทียบ model แต่เรายังไม่ได้ implement Stage 08
7. จำนวน features ของ Extract Set 2/3 ยังไม่ตรง paper
8. Baseline performance ของเราสูงมาก ควรตรวจว่า target definition, diagnosis timing, medication flags หรือ disease flags มี proxy leakage หรือไม่

## สิ่งที่ควรทำต่อเพื่อให้เหมือน Paper มากขึ้น

1. ตรวจ data dictionary ของ `smoke`, `drinking`, `sex`, medication flags และ diagnosis fields
2. ตรวจว่า features บางตัว เช่น `heart_disease`, `hypertension`, `diabetes`, medication flags ถูกสร้างจากข้อมูลก่อน reference date จริงหรือเป็น summary ทั้ง patient
3. ทำ sensitivity analysis ของ temporal windows:
   - paper default: 21-9, 18-6, 15-3 เดือน
   - alternative: 90/180 วัน
   - alternative: relaxed completeness เช่น มีอย่างน้อยบาง core labs ไม่ใช่ครบทุกตัว
4. ปรับ Extract Set 2/3 ให้ตรงจำนวนและนิยาม paper ถ้าต้องการ replication แบบ strict
5. Implement Stage 07:
   - ANOVA F-test
   - PCA
   - ANOVA + PCA
6. Implement Stage 08:
   - final validation report
   - McNemar's test
   - baseline vs temporal comparison
7. เพิ่ม leakage audit เชิงลึก:
   - ตรวจ diagnosis-derived comorbidities
   - ตรวจ medication flags
   - ตรวจว่าข้อมูลโรคร่วมไม่ได้ถูกสร้างจากอนาคตหลัง reference date
8. เพิ่ม test cases สำหรับ:
   - ICD detection
   - reference date logic
   - post-reference removal
   - window assignment
   - one-row-per-patient feature tables

## สรุปตัดสิน

สถานะปัจจุบัน: **เหมือน paper ในระดับ pipeline design และ preprocessing/feature-engineering concept แต่ยังไม่เหมือน paper ในระดับ experimental replication และผลลัพธ์**

เหตุผลหลักคือ strict temporal completeness ทำให้ข้อมูลที่ใช้ temporal model เหลือเพียง 13 patients และมี stroke positive เพียง 1 ราย จึงยังไม่สามารถ train temporal models, ทำ ANOVA/PCA comparison หรือทดสอบ McNemar แบบ paper ได้

ดังนั้นงานเราตอนนี้ควรถือว่าเป็น **implementation scaffold ที่เดินตาม paper แล้ว** แต่ยังต้องปรับ cohort/window/completeness strategy ก่อนจึงจะเป็น **full replication / comparable experiment** ได้

