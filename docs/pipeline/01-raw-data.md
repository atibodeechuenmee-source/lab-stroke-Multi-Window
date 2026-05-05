# Raw Data

## Goal

ตรวจสอบข้อมูลต้นทางให้เข้าใจ schema, ชนิดข้อมูล, ความครบถ้วน และข้อจำกัดก่อนนำไป cleaning หรือ modeling

## Inputs

- `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Data dictionary: `DATASET.md`

## Steps

1. โหลดไฟล์ raw Excel โดยไม่แก้ค่าต้นฉบับ
2. ตรวจจำนวน rows, columns และชื่อ columns
3. ตรวจ dtype เบื้องต้น เช่น date, numeric, flag, text
4. ตรวจคอลัมน์สำคัญ เช่น `hn`, `vstdate`, `PrincipleDiagnosis`, `age`, vitals, labs, medication flags
5. บันทึก schema summary และ missing summary เพื่อใช้เทียบกับขั้นตอนถัดไป

## Outputs

- Raw schema summary
- Column availability checklist
- Missing summary เบื้องต้น
- รายการคอลัมน์ที่ต้องใช้ใน target, cohort, cleaning, feature engineering

## Checks

- ห้ามเขียนทับ raw file
- ตรวจว่า `hn` และ `vstdate` มีอยู่ก่อนทำ patient-level workflow
- ตรวจว่า `PrincipleDiagnosis` มีอยู่ก่อนสร้าง stroke target
- ตรวจชื่อคอลัมน์ที่มีอักขระพิเศษ เช่น `TC:HDL_ratio`
