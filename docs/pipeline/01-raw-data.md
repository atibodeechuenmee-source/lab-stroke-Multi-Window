# Stage 01: Raw Data

## Purpose

ตรวจสอบ raw EHR data ก่อนเริ่ม cleaning หรือ cohort construction เพื่อให้รู้ว่า dataset มี column ใดบ้าง, data type เป็นอย่างไร, stroke ICD code อยู่ใน field ไหน, และมีข้อมูลเพียงพอสำหรับ temporal feature engineering หรือไม่

## Input

- Raw data file ใน `data/raw`
- Expected source: EHR records ระดับ visit/record
- Paper reference: `paper/multi-window-temporal-features-stroke-risk-2026.md`

Expected raw fields ควรครอบคลุม:

- Patient identifier เช่น `HN` หรือ anonymized patient id
- Visit date หรือ service date
- Diagnosis fields เช่น principal diagnosis และ comorbidity diagnosis
- ICD-10 codes
- Blood pressure: BPS, BPD
- Lipid labs: HDL, LDL, total cholesterol, triglycerides
- FBS
- BMI, height, weight ถ้ามี
- eGFR, creatinine
- Age, sex
- Smoking, drinking
- Atrial fibrillation
- Medication fields เช่น statin และ antihypertensive drugs

## Process

1. โหลด raw file แบบ read-only
2. สร้าง raw schema summary ได้แก่ column name, inferred type, missing count, missing percent, example values
3. ตรวจว่ามี patient id และ visit date ที่ใช้สร้าง longitudinal sequence ได้
4. ตรวจ diagnosis fields ว่าสามารถ map ICD-10 `I60-I68` ได้หรือไม่
5. ตรวจ unit และ value range เบื้องต้นของ labs และ vital signs
6. ตรวจจำนวน records ต่อ patient และช่วงเวลาครอบคลุมของข้อมูล
7. สร้าง data dictionary ฉบับแรกสำหรับส่งต่อ stage cleaning

## Output

- Raw column list
- Raw schema summary
- Missingness summary
- Visit coverage summary ต่อ patient
- ICD-10 availability report
- รายการ columns ที่ต้อง rename หรือ standardize

## Checks / Acceptance Criteria

- พบ patient identifier ที่ใช้ group records เป็น patient-level ได้
- พบ date column ที่ใช้ sort visits และสร้าง temporal windows ได้
- พบ diagnosis/ICD fields ที่ใช้สร้าง stroke target ได้
- พบ core clinical variables เพียงพอสำหรับสร้าง Extract Set 1/2/3 หรือระบุ missing columns ไว้ชัดเจน
- ยังไม่มีการลบหรือแก้ raw data ใน stage นี้

## Relation to Paper

Paper ใช้ real-world EHR จำนวนมากและเลือก clinical variables จาก raw attributes ก่อนสร้าง temporal windows ดังนั้น stage นี้ทำหน้าที่เทียบ raw data ของเรากับ variable requirements ของ paper ก่อนเริ่ม cohort construction

