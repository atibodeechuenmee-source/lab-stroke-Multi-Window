# Deployment Optional

## Goal

เตรียมแนวทางนำโมเดลไปใช้งานจริงเฉพาะเมื่อ validation เพียงพอ และมี input contract, monitoring และ retraining plan ที่ชัดเจน

## Inputs

- Final trained pipeline
- Feature list และ preprocessing rules
- Validation report
- Input data schema

## Steps

1. บันทึก model artifact พร้อม preprocessing pipeline
2. กำหนด input contract เช่น required columns, dtype, valid ranges
3. สร้าง inference script ที่รับ raw/cleaned input และคืน predicted probability
4. กำหนด threshold สำหรับ action ตาม clinical/business requirement
5. วาง monitoring สำหรับ missing rate, feature drift, target drift และ model performance
6. วาง retraining plan เมื่อข้อมูลหรือ performance เปลี่ยน

## Outputs

- Model artifact
- Inference script หรือ API spec
- Input schema contract
- Monitoring checklist
- Retraining notes

## Checks

- Deployment เป็น optional และควรทำหลัง validation ผ่านเท่านั้น
- Inference preprocessing ต้องเหมือน training preprocessing
- ต้องมี fallback เมื่อ input ขาดคอลัมน์สำคัญ
- ห้ามใช้โมเดลเพื่อการตัดสินใจทางคลินิกโดยไม่มี human review และ validation ที่เหมาะสม
