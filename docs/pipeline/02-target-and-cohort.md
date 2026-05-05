# Target & Cohort Definition

## Goal

นิยาม outcome และประชากรที่ใช้วิเคราะห์ให้ชัดเจนก่อน cleaning, EDA และ modeling เพื่อลด ambiguity และป้องกัน leakage

target หลักของโจทย์นี้คือ `stroke_3m` ระดับคนไข้: คนไข้มี primary stroke diagnosis ภายใน 90 วันหลัง index date หรือไม่

## Inputs

- Raw data
- `hn` สำหรับ patient id
- `vstdate` สำหรับ timeline
- `PrincipleDiagnosis` สำหรับนิยาม stroke outcome

## Steps

1. แปลง `vstdate` เป็น datetime ด้วย invalid date เป็น missing
2. สร้าง `stroke_flag` เป็น event marker ระดับแถวจาก `PrincipleDiagnosis` ที่เป็น ICD-10 ช่วง `I60-I69*`
3. ใช้ `stroke_flag` เพื่อหา stroke event date แรกของแต่ละคน
4. กำหนด index date, event date, และ horizon 90 วันสำหรับ patient-level 90-day prediction
5. สร้าง target หลัก `stroke_3m` ระดับคนไข้
6. ตัดข้อมูลหลัง index date ออกจาก feature source ใน patient-level workflow

## Outputs

- Event marker ระดับแถว: `stroke_flag`
- Target หลักระดับคนไข้: `stroke_3m`
- Cohort summary เช่น จำนวน patients, records, positives, negatives, prevalence
- Exclusion summary สำหรับ record/patient ที่ไม่เข้าเงื่อนไข

## Checks

- ไม่ใช้ `PrincipleDiagnosis` เป็น model feature เพราะใช้สร้าง target
- ไม่ใช้ diagnosis/text หลัง index date เป็น feature
- ตรวจ class imbalance ของ `stroke_3m` เป็นหลัก
- ตรวจว่าผู้ป่วย positive มี event ภายใน horizon ที่กำหนดจริง
