# Stage 08: Validation

## Purpose

ประเมิน model performance อย่างเหมาะสมกับ imbalanced stroke prediction และตรวจว่าการใช้ temporal features ดีกว่า single-shot baseline อย่างมีนัยสำคัญหรือไม่

## Input

- Patient-level labels จาก Stage 02
- Predictions จาก baseline และ temporal models จาก Stage 06
- Feature selection/PCA results จาก Stage 07
- Cohort attrition และ EDA summaries จาก Stage 02/04

## Process

1. Performance metrics:
   - sensitivity
   - specificity
   - G-Mean
   - ROC-AUC optional
   - PR-AUC optional
2. G-Mean เป็น metric หลัก:

```text
G-Mean = sqrt(Sensitivity * Specificity)
```

3. Baseline comparison:
   - เปรียบเทียบ single-shot baseline กับ Extract Set 1/2/3
   - เปรียบเทียบ no reduction, ANOVA, PCA, ANOVA+PCA
4. McNemar's test:
   - ใช้ paired predictions ของ baseline และ temporal model
   - รายงาน disagreement counts, chi-square และ p-value
5. Leakage audit:
   - ตรวจว่า validation predictions มาจาก features ก่อน reference date เท่านั้น
   - ตรวจว่า feature selection/PCA fit เฉพาะ training folds
6. Cohort attrition review:
   - รายงานจำนวน patients ก่อน/หลัง completeness criteria
   - ระบุผลกระทบของ strict temporal windows ต่อ sample size

## Output

- Validation report
- Confusion matrix ต่อ model
- Sensitivity/specificity/G-Mean table
- ROC-AUC/PR-AUC table ถ้ามี
- McNemar's test report
- Leakage audit report
- Cohort attrition report

## Checks / Acceptance Criteria

- ทุก model มี sensitivity, specificity และ G-Mean
- รายงาน single-shot baseline แยกจาก temporal models
- มี McNemar's test อย่างน้อยหนึ่งคู่: best temporal model vs single-shot baseline
- ไม่มี metric ที่คำนวณจาก post-reference features
- ระบุ model ที่ดีที่สุดด้วย G-Mean ไม่ใช่ accuracy อย่างเดียว
- รายงานข้อจำกัดจาก class imbalance และ sample size

## Relation to Paper

Paper ใช้ G-Mean เพราะข้อมูล imbalance สูง และใช้ McNemar's test เพื่อพิสูจน์ว่า temporal model ดีกว่า baseline อย่างมีนัยสำคัญ Stage นี้จึงทำหน้าที่เป็น evidence layer ของ pipeline

