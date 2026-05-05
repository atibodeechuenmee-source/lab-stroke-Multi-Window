# Validation

## Goal

ตรวจว่าโมเดลทำงานได้จริงบนข้อมูลที่ไม่เคยเห็น และประเมินความเสี่ยงก่อนนำผลไปใช้ตัดสินใจหรือรายงาน

## Inputs

- Trained model
- Holdout test set
- CV metrics
- Feature importance/SHAP outputs

## Steps

1. สรุป holdout metrics เช่น ROC-AUC, PR-AUC, precision, recall, F1
2. ตรวจ confusion matrix ที่ threshold หลัก เช่น 0.5
3. ทำ threshold tuning ถ้าต้องการเน้น recall หรือ precision
4. ตรวจ calibration ถ้าต้องใช้ predicted probability
5. ทำ sensitivity analysis เช่น horizon 90 วัน เทียบกับ horizon อื่น ถ้าจำเป็น
6. ทำ leakage audit ของ feature list และ preprocessing steps
7. สรุป limitation ของ dataset, target definition, missing data และ model performance

## Outputs

- Validation report
- Holdout metric table
- Threshold analysis
- Calibration summary ถ้ามี
- Leakage audit checklist
- Final model recommendation

## Checks

- Validation ต้องไม่ใช้ข้อมูลที่ถูกใช้เลือก preprocessing/model โดยตรง
- PR-AUC สำคัญมากเมื่อ positive class น้อย
- ตรวจ recall ของ stroke class แยกจาก overall accuracy
- รายงานข้อจำกัดก่อนสรุปว่าโมเดลพร้อมใช้งาน
