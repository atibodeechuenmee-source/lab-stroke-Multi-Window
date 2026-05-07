# Stage 07: Feature Importance and Dimensionality Reduction

## Purpose

ประเมิน feature importance และ dimensionality reduction ตาม paper โดยเปรียบเทียบ ANOVA F-test, PCA และ ANOVA+PCA บน Extract Set 1/2/3

## Input

- Extract Set 1/2/3 จาก Stage 05
- Labels จาก Stage 02/05
- Model context จาก Stage 06

## Process

1. ANOVA F-test:
   - rank numerical features by F-score / p-value
   - test forward top-k เช่น 5, 10, 15, 20, 30, 40, 50
   - choose k by G-Mean under CV

2. PCA:
   - impute missing values within training fold
   - standardize numerical features within training fold
   - fit PCA within training fold
   - test different component counts
   - choose component count by G-Mean

3. ANOVA + PCA:
   - select top-k features with ANOVA
   - run PCA on selected features
   - train Logistic Regression
   - compare against ANOVA-only and PCA-only

4. Interpretability:
   - ANOVA ranking remains original-feature interpretable
   - PCA components are less directly interpretable
   - report this limitation clearly

## Output

- `feature_importance_summary.csv`
- `anova_feature_ranking.csv`
- `anova_performance.csv`
- `pca_performance.csv`
- `anova_pca_performance.csv`
- `best_feature_importance_choices.csv`
- `feature_importance_report.json`
- `feature_importance_report.md`

## Checks / Acceptance Criteria

- Feature selection must happen inside training fold
- Scaler/PCA must fit on training fold only
- Must report best k/component count for each Extract Set when possible
- Must report skipped sets with reason when class distribution is insufficient
- Must not use test fold information for feature ranking in model evaluation
- Must explain interpretability loss from PCA

## Relation to Paper

Paper ใช้ ANOVA F-test, PCA และ ANOVA+PCA เพื่อจัดการ feature dimensionality และ multicollinearity ของ temporal features Stage นี้จึงเป็นส่วนสำคัญในการทำตาม experiment ของ paper ไม่ใช่แค่ optional analysis
