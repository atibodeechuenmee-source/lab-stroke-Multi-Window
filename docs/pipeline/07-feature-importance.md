# Stage 07: Feature Importance and Dimensionality Reduction

## Purpose

ประเมิน feature importance และลดมิติของ temporal features เพื่อเปรียบเทียบ ANOVA F-test, PCA และ ANOVA ตามด้วย PCA ตามแนวทาง paper

## Input

- Extract Set 1/2/3 feature tables จาก Stage 05
- Stroke labels จาก Stage 02
- Model predictions/configs จาก Stage 06

## Process

1. ANOVA F-test:
   - rank numerical features ตาม F-score หรือ p-value
   - ทดลอง top-k features เช่น 5, 10, 15, 20, 30, 40, 50
   - เลือก k จาก G-Mean บน CV
2. PCA:
   - standardize numerical features ก่อน PCA
   - ทดลองจำนวน components หลายค่า
   - เลือกจำนวน components จาก G-Mean บน CV
3. ANOVA + PCA:
   - เลือก top-k features ด้วย ANOVA
   - ทำ PCA บน selected features
   - train Logistic Regression และเปรียบเทียบกับวิธีอื่น
4. Model interpretability:
   - Logistic Regression coefficients สำหรับ features ที่ไม่ผ่าน PCA
   - Feature importance สำหรับ Random Forest/XGBoost ถ้ามี
   - ระบุข้อจำกัดว่า PCA ลด interpretability

## Output

- ANOVA feature ranking
- PCA component performance table
- ANOVA + PCA performance table
- Selected features/components
- Feature importance report
- Interpretability notes

## Checks / Acceptance Criteria

- Feature selection ต้องทำภายใน training fold เพื่อหลีกเลี่ยง leakage
- PCA scaler และ PCA model ต้อง fit เฉพาะ training data ในแต่ละ fold
- รายงาน best k หรือ best component count สำหรับ Extract Set 1/2/3
- ระบุชัดว่า feature importance จาก PCA ตีความโดยตรงไม่ได้เท่า original features
- Output ต้องพร้อมใช้เปรียบเทียบใน validation stage

## Relation to Paper

Paper เปรียบเทียบ ANOVA F-test, PCA และ ANOVA+PCA เพื่อจัดการ feature dimensionality และ multicollinearity ของ temporal features Stage นี้จึงทำหน้าที่จำลอง analysis นั้นในโปรเจกต์ของเรา

