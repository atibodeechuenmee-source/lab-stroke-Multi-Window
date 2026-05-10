# Stage 09: Deployment Notes (Optional)

## Purpose

บันทึกข้อควรพิจารณาหากนำ pipeline ไปต่อยอดเป็น clinical decision-support system โดยยังยึดข้อจำกัดและแนวคิดจาก paper

Stage นี้ optional เพราะ paper ยังเป็นงานวิจัยเชิง framework ไม่ใช่ระบบ deploy จริง

## Input

- Best model and validation report จาก Stage 08
- Feature dictionary จาก Stage 05
- Cohort/attrition report จาก Stage 02
- Leakage audit จาก Stage 04/08
- Paper limitations

## Process

1. Define inference-time requirements:
   - patient id
   - visit date
   - clinical labs
   - diagnosis
   - medication/risk factors
   - enough visits in required windows
   - overlapping FIRST/MID/LAST coverage when temporal model is used
2. Check whether a patient has enough temporal coverage
3. Fall back rules:
   - if temporal completeness fails, use single-shot baseline
   - report uncertainty / insufficient longitudinal history
4. Interpretability:
   - Logistic Regression coefficients for non-PCA models
   - ANOVA-selected features for explanation
   - PCA models need component-level caution
5. Monitoring:
   - missingness drift
   - visit frequency drift
   - lab availability drift
   - stroke prevalence drift
   - performance drift
6. External validation:
   - validate on another hospital/site
   - validate on later time period
   - compare with paper cohort and local cohort

## Output

- Deployment readiness notes
- Inference input requirements
- Monitoring checklist
- External validation plan
- Clinical risk and limitation notes

## Checks / Acceptance Criteria

- Must state that current model is research-stage unless externally validated
- Must not hide temporal-completeness limitations
- Must include fallback for insufficient window coverage
- Must document that FIRST/MID/LAST are overlapping retrospective windows
- Must include monitoring plan
- Must include clinician-review requirement before real use

## Relation to Paper

Paper proposes a framework for more robust stroke-risk stratification using routine hospital EHR, but does not provide production deployment evidence. Stage นี้จึงแปลข้อค้นพบของ paper เป็น deployment cautions และ next steps โดยไม่กล่าวเกินหลักฐาน
