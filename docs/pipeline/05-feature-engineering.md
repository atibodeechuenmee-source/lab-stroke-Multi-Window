# Feature Engineering

## Goal

สร้างตัวแปรที่สะท้อนประวัติผู้ป่วย ภาวะเสี่ยง การใช้ยา และ pattern ของ lab/vital โดยไม่ใช้ข้อมูลอนาคตหรือ target leakage

## Inputs

- Cleaned dataset
- Target/cohort definition
- `hn`, `vstdate`, demographic, vitals, labs, comorbidity flags, medication flags
- Implementation script: `src/feature_engineering.py`

## Steps

1. สร้าง date features เช่น visit year, visit month หรือ time-based features ที่จำเป็น
2. สร้าง latest features จากข้อมูลก่อนหรือ ณ index date เช่น age, BMI, smoke, diabetes, hypertension, medication flags
3. สร้าง temporal summary สำหรับ vitals/labs เช่น latest, mean, min, max, std, count
4. สร้าง missing-rate features สำหรับ labs/vitals ที่ missing สูง
5. สร้าง history features เช่น visit count และ observation window
6. เลือกหรือ exclude text/diagnosis fields ตาม leakage risk

## Outputs

- Feature table สำหรับ modeling
- Feature list พร้อมคำอธิบาย
- Feature generation log
- Missing indicator และ missing-rate features ตามที่กำหนด
- Output หลัก: `data/processed/patient_level_90d_stroke.csv`
- Report: `output/feature_engineering_output/feature_engineering_report.md`

## Checks

- Patient-level features ต้องใช้เฉพาะข้อมูลก่อนหรือ ณ index date
- ห้ามใช้ diagnosis ที่นิยาม outcome เป็น feature
- ตรวจว่าทุก feature คำนวณซ้ำได้จาก raw/cleaned data
- ตรวจจำนวน rows หลัง aggregate เทียบกับจำนวน patients/cohort
