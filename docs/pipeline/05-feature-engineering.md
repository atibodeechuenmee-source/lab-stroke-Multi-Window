# Stage 05: Temporal Feature Engineering

## Purpose

สร้าง feature tables ตาม Feature Extraction ของ paper โดยมีทั้ง `single-shot baseline` และ temporal Extract Set 1/2/3

## Input

- `cleaned_pre_reference_records.csv` จาก Stage 03
- Temporal windows จาก Stage 02:
  - FIRST
  - MID
  - LAST
- Temporal completeness flags

## Process

1. Compute `TC:HDL` ถ้ายังไม่มี:

```text
TC:HDL = Total Cholesterol / HDL
```

2. Build single-shot baseline:
   - ใช้ latest pre-reference record ต่อ patient
   - เป็น comparator หลักของ paper

3. Apply temporal-complete cohort:
   - ต้องมี visit ในทุก FIRST/MID/LAST
   - ต้องมี core clinical variables ครบทุก window

4. Build Extract Set 1:
   - paper target: 35 features
   - core demographic + clinical variables
   - 10 numerical variables across 3 windows
   - 5 categorical features

5. Build Extract Set 2:
   - paper target: 115 features
   - เพิ่ม statistical/temporal descriptors:
     - mean
     - min
     - max
     - standard deviation
     - first
     - last
     - delta
     - slope
     - cross-window min/max differences
     - measurement count differences

```text
Delta(X) = X_LAST - X_FIRST
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST)
```

6. Build Extract Set 3:
   - paper target: 121 features
   - เพิ่ม diabetes, hypertension, heart disease, statin, antihypertensive, TC:HDL

7. Build feature dictionary:
   - feature name
   - source column
   - source window
   - aggregation
   - feature set

8. Build exclusions:
   - patients excluded from temporal sets
   - reason for exclusion

## Output

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- `temporal_completeness_flags.csv`
- `feature_dictionary.csv`
- `feature_generation_log.csv`
- `feature_engineering_exclusions.csv`
- `feature_engineering_report.json`
- `feature_engineering_report.md`

## Checks / Acceptance Criteria

- Single-shot baseline must use latest pre-reference record only
- Temporal features must use FIRST/MID/LAST only
- No feature may use post-reference records
- Feature dictionary must trace feature origin
- Extract Set 1/2/3 must be generated separately
- Report actual feature counts and compare with paper targets 35/115/121

## Relation to Paper

Stage นี้ตรงกับ Feature Extraction ของ paper โดยตรง เป็นหัวใจของงาน เพราะ paper แสดงว่า temporal representations เพิ่ม predictive value เหนือ single-shot baseline
