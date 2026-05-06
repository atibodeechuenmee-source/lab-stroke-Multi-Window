# Stage 04: Exploratory Data Analysis

## Purpose

ทำ EDA เพื่อประเมินความพร้อมของข้อมูลสำหรับ temporal stroke-risk prediction โดยเน้น class imbalance, missingness, visit coverage, temporal window coverage และความต่างระหว่าง stroke กับ non-stroke

## Input

- Cleaned pre-reference records จาก Stage 03
- Patient-level cohort จาก Stage 02
- Window assignment: FIRST, MID, LAST

## Process

1. Class imbalance:
   - นับ stroke และ non-stroke patients
   - รายงาน stroke prevalence หลัง cohort filtering
2. Visit frequency:
   - จำนวน visits ต่อ patient
   - จำนวน visits ต่อ temporal window
   - distribution ของ time gap ระหว่าง visits
3. Missingness:
   - missing percent ราย variable
   - missingness แยกตาม stroke/non-stroke
   - missingness แยกตาม FIRST/MID/LAST
4. Temporal coverage:
   - จำนวน patient ที่ครบทุก window
   - จำนวน patient ที่หลุดเพราะ window coverage ไม่พอ
   - sensitivity note สำหรับ alternative windows เช่น 90/180 วัน
5. Clinical distribution:
   - distribution ของ BPS, BPD, HDL, LDL, FBS, BMI, eGFR, creatinine, total cholesterol, triglycerides
   - เปรียบเทียบ stroke vs non-stroke
6. Leakage audit เบื้องต้น:
   - ตรวจว่าไม่มีค่า lab, diagnosis หรือ medication หลัง reference date ใน EDA set

## Output

- EDA summary report
- Class imbalance table
- Missingness tables
- Visit coverage summary
- Temporal coverage summary
- Stroke vs non-stroke descriptive statistics
- Leakage audit summary

## Checks / Acceptance Criteria

- มีรายงาน stroke/non-stroke count ระดับ patient
- มีรายงาน visit coverage แยก FIRST, MID, LAST
- ระบุ variables ที่ missing สูงหรือไม่พร้อมใช้ temporal features
- ระบุว่า completeness criteria ทำให้ sample ลดลงมากแค่ไหน
- ไม่ใช้ข้อมูลหลัง reference date ใน plot หรือ summary ใด ๆ

## Relation to Paper

Paper ใช้ strict temporal alignment และ completeness criteria ซึ่งอาจลด sample จำนวนมาก Stage นี้จึงต้องตรวจให้เห็นก่อนว่า dataset ของเรารองรับ multi-window temporal modeling ได้ดีแค่ไหน

