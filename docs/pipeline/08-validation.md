# Stage 08: Validation

## Purpose

ทำ validation ตาม paper เพื่อพิสูจน์ว่า temporal representations ให้ผลดีกว่า single-shot baseline อย่างมีความหมาย โดยเน้น metrics สำหรับ imbalanced clinical data

## Input

- Prediction files จาก Stage 06
- Feature selection/PCA results จาก Stage 07
- Cohort attrition จาก Stage 02
- Leakage audit จาก Stage 04

## Process

1. Build metrics table:
   - sensitivity
   - specificity
   - G-Mean
   - ROC-AUC when available
   - PR-AUC when available

2. Use G-Mean as primary metric:

```text
G-Mean = sqrt(Sensitivity * Specificity)
```

3. Compare model groups:
   - single-shot baseline
   - Extract Set 1
   - Extract Set 2
   - Extract Set 3
   - no reduction
   - ANOVA
   - PCA
   - ANOVA+PCA

4. McNemar's test:
   - compare paired predictions
   - baseline vs best temporal model
   - report disagreement counts
   - report chi-square and p-value

5. Leakage audit:
   - confirm no post-reference features
   - confirm fold-local feature selection/PCA

6. Cohort attrition review:
   - report raw cohort
   - report post-reference cohort
   - report temporal-complete cohort
   - explain effect of strict completeness

## Output

- `validation_metrics.csv`
- `validation_confusion_matrices.csv`
- `roc_pr_auc_table.csv`
- `baseline_vs_temporal_comparison.csv`
- `mcnemar_test_report.csv`
- `leakage_audit_report.csv`
- `cohort_attrition_validation_view.csv`
- `validation_summary.json`
- `validation_report.md`

## Checks / Acceptance Criteria

- Every completed model must have sensitivity, specificity, G-Mean
- Baseline must be separated from temporal models
- McNemar report must exist even if skipped with reason
- Best model must be selected by G-Mean
- Validation must not compute metrics from post-reference features
- Must explicitly report sample-size/class-imbalance limitations

## Relation to Paper

Paper ใช้ G-Mean เพราะข้อมูล imbalance สูง และใช้ McNemar's test เพื่อยืนยันว่า temporal model เหนือกว่า baseline อย่างมีนัยสำคัญ Stage นี้จึงเป็น evidence layer สำคัญที่สุดของ pipeline
