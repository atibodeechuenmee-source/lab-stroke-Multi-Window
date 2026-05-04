# EDA และ Feature Importance Slide Notes

โฟลเดอร์นี้เก็บเอกสาร Markdown สำหรับเตรียมเด็ค 10 สไลด์เรื่อง Exploratory Data Analysis และ Feature Importance ของงาน stroke prediction เท่านั้น ยังไม่สร้างไฟล์ PPTX

## ควรเริ่มอ่านจากไฟล์ไหน

1. `slide-plan.md` - โครงเรื่องหลักของเด็ค 10 สไลด์ พร้อม key message, visual asset, source file และ speaker goal
2. `presenter-script.md` - สคริปต์พูดภาษาไทยตามลำดับสไลด์ 1-10
3. `assets-needed.md` - รายการกราฟและตารางจาก `output/eda_output/` และ `output/feature_importance_output/` ที่ต้องใช้ตอนทำสไลด์จริง
4. `build-notes.md` - ข้อกำหนดด้าน tone, visual style, caveat และข้อห้ามในการตีความ

## ขอบเขต

เอกสารชุดนี้ครอบคลุมเฉพาะ:

- Dataset overview สำหรับ EDA
- Feature groups
- Missing values
- Summary statistics, correlation และ outlier
- Feature importance pipeline
- Random Forest, XGBoost, RF feature importance และ SHAP interpretation
- Caveat เรื่อง missing values, class imbalance, leakage และ non-causal interpretation

เอกสารชุดนี้ไม่ครอบคลุมงานนอกขอบเขต EDA และ feature importance
