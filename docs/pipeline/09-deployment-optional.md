# Stage 09: Deployment Optional

## Purpose

บันทึกข้อพิจารณาหากต้องนำ temporal stroke-risk model ไปใช้เป็น clinical decision-support system ในอนาคต โดย stage นี้ยังเป็น optional และไม่ใช่การ deploy จริง

## Input

- Best validated model จาก Stage 08
- Feature dictionary จาก Stage 05
- Validation report จาก Stage 08
- Known limitations จาก paper และจากข้อมูลของเรา

## Process

1. Inference-time requirements:
   - ต้องมี patient id
   - ต้องมี visit history ก่อน prediction date
   - ต้องสร้าง FIRST/MID/LAST windows ได้
   - ต้องมี core clinical variables ครบตาม feature set ที่เลือก
2. Prediction date:
   - production setting ต้องกำหนด prediction date แทน reference date
   - ห้ามใช้ future records หลัง prediction date
3. Model output:
   - predicted probability
   - risk group ถ้ามี threshold ที่ validate แล้ว
   - explanation หรือ feature contribution สำหรับ clinical review
4. Monitoring:
   - class distribution drift
   - missingness drift
   - lab/unit drift
   - model calibration drift
   - sensitivity/specificity drift เมื่อมี outcome ย้อนหลัง
5. External validation:
   - ต้องทดสอบกับโรงพยาบาลหรือช่วงเวลาที่ไม่อยู่ใน training data
   - ต้องตรวจว่า temporal window coverage ยังใช้ได้กับ workflow จริง

## Output

- Deployment readiness checklist
- Inference data requirements
- Monitoring plan
- External validation plan
- Clinical safety notes

## Checks / Acceptance Criteria

- ระบุชัดว่า stage นี้ optional และยังไม่ใช่ production deployment
- inference logic ไม่ใช้ข้อมูลหลัง prediction date
- ระบุ required features และ required temporal history
- ระบุ limitation ของ model ก่อนใช้งานจริง
- ต้องมี external validation ก่อน clinical use

## Relation to Paper

Paper สรุปว่า temporal features เพิ่มความน่าเชื่อถือของ decision support เมื่อเทียบกับ single-time-point approaches แต่ยังมีข้อจำกัดด้าน sample size, real-world missingness และ external validation Stage นี้จึงบันทึกเงื่อนไขก่อนต่อยอดสู่การใช้งานจริง

