# Target & Cohort Definition

## Goal

นิยาม outcome และประชากรที่ใช้วิเคราะห์ให้ชัดเจนก่อน cleaning, EDA และ modeling เพื่อลด ambiguity และป้องกัน leakage

## Inputs

- Raw data
- `hn` สำหรับ patient id
- `vstdate` สำหรับ timeline
- `PrincipleDiagnosis` สำหรับนิยาม stroke outcome

## Steps

1. แปลง `vstdate` เป็น datetime ด้วย invalid date เป็น missing
2. สร้าง stroke flag จาก `PrincipleDiagnosis` ที่เป็น ICD-10 ช่วง `I60-I69*`
3. ถ้าใช้ record-level modeling ให้ระบุว่า 1 row คือ 1 visit/record
4. ถ้าใช้ patient-level 90-day prediction ให้กำหนด index date, event date, และ horizon 90 วัน
5. ตัดข้อมูลหลัง index date ออกจาก feature source ใน patient-level workflow

## Outputs

- Target column เช่น `stroke_flag` หรือ `stroke_3m`
- Cohort summary เช่น จำนวน patients, records, positives, negatives, prevalence
- Exclusion summary สำหรับ record/patient ที่ไม่เข้าเงื่อนไข

## Checks

- ไม่ใช้ `PrincipleDiagnosis` เป็น model feature เพราะใช้สร้าง target
- ไม่ใช้ diagnosis/text หลัง index date เป็น feature
- ตรวจ class imbalance ของ target
- ตรวจว่าผู้ป่วย positive มี event ภายใน horizon ที่กำหนดจริง
