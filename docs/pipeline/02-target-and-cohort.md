# Stage 02: Target and Cohort

## Purpose

สร้าง patient-level cohort และ target variable สำหรับ stroke-risk prediction โดยกำหนด `reference date` อย่างชัดเจน และตัด records หลัง reference date เพื่อป้องกัน data leakage

## Input

- Raw หรือ lightly standardized EHR records จาก Stage 01
- Patient id
- Visit date
- ICD-10 diagnosis fields
- Core clinical variables สำหรับ temporal feature extraction

## Process

1. ระบุ stroke event จาก ICD-10 codes `I60-I68`
2. สร้าง patient-level stroke label:
   - `stroke = 1` ถ้าผู้ป่วยมี ICD-10 `I60-I68` อย่างน้อยหนึ่งครั้ง
   - `stroke = 0` ถ้าไม่พบ stroke event ใน records
3. กำหนด `reference date`:
   - stroke patient: วันที่เกิด stroke ครั้งแรก
   - non-stroke patient: วันที่ visit ล่าสุด
4. ลบ records ที่เกิดหลัง `reference date`
5. สร้าง temporal windows:
   - FIRST: 21-9 เดือนก่อน reference date
   - MID: 18-6 เดือนก่อน reference date
   - LAST: 15-3 เดือนก่อน reference date
6. ตรวจ temporal completeness:
   - ต้องมีอย่างน้อย 1 visit ในทุก window
   - core clinical variables ต้องมีครบในทุก window สำหรับ temporal feature extraction
7. สร้าง cohort attrition table เพื่อแสดงจำนวน patient ที่ถูกคัดออกในแต่ละเงื่อนไข

## Output

- Patient-level cohort table
- Patient id, stroke label, reference date
- Pre-reference records เท่านั้น
- Window assignment สำหรับแต่ละ record
- Cohort attrition report
- Temporal completeness flags

## Checks / Acceptance Criteria

- ไม่มี record ที่ visit date มากกว่า reference date ใน output
- Stroke patient ทุกคนมี reference date เป็น first stroke date เท่านั้น
- Non-stroke patient ทุกคนมี reference date เป็น last visit date
- ทุก patient ที่ผ่าน final cohort มี FIRST, MID, LAST ครบ
- รายงานจำนวน excluded patients แยกตามเหตุผลได้

## Relation to Paper

Stage นี้เป็นแกนหลักของ paper เพราะ paper สร้าง temporal representation จาก three retrospective windows และใช้ strict completeness criteria ก่อน model training

