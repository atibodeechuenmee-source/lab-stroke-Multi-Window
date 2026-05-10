# Stage 05: Temporal Feature Engineering

## Purpose

สร้าง feature tables ตาม Feature Extraction ของ paper โดยมีทั้ง `single-shot baseline` และ temporal Extract Set 1/2/3

Stage นี้ต้องใช้ overlapping FIRST/MID/LAST windows จาก Stage 02 ให้ถูกต้อง เพราะนี่เป็นหัวใจของ multi-window temporal representation ใน paper

## Input

- `cleaned_pre_reference_records.csv` จาก Stage 03
- Windowed pre-reference records จาก Stage 02 ใน long format:
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
   - window membership ต้องมาจาก overlapping windows ไม่ใช่ exclusive label

4. Aggregate records by `patient_id + window`

Because windows overlap, the same source medical record may contribute to multiple window-level aggregations. This is expected and matches the paper figure.

Example:

```text
12 months before reference date -> contributes to FIRST, MID, LAST
8 months before reference date  -> contributes to MID, LAST
4 months before reference date  -> contributes to LAST only
```

5. Build Extract Set 1:
   - paper target: 35 features
   - `10 numerical variables x 3 windows = 30`
   - `5 static/categorical features = 5`

6. Build Extract Set 2:
   - paper target: 115 features
   - `11 temporal/statistical descriptors x 10 numerical variables = 110`
   - `5 static/categorical features = 5`
   - descriptors include mean, minimum, maximum, standard deviation, first value, last value, delta, slope, cross-window differences, and measurement-count differences

```text
Delta(X) = X_LAST - X_FIRST
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST)
```

7. Build Extract Set 3:
   - paper target: 121 features
   - Extract Set 2 + 6 risk factors:
     - diabetes
     - hypertension
     - heart disease
     - statin
     - antihypertensive
     - TC:HDL

8. Build feature dictionary:
   - feature name
   - source column
   - source window
   - aggregation
   - feature set
   - whether source record can appear in overlapping windows

9. Build exclusions:
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
- FIRST/MID/LAST must be treated as overlapping windows
- A source record in overlap ranges must be allowed to contribute to multiple windows
- No feature may use post-reference records or prediction-window records
- Feature dictionary must trace feature origin
- Extract Set 1/2/3 must be generated separately
- Actual feature counts must match paper targets 35/115/121

## Relation to Paper

Stage นี้ตรงกับ Feature Extraction ของ paper โดยตรง และต้องใช้ overlapping multi-window representation ตามภาพใน paper ไม่ใช่ mutually exclusive binning

ถ้า Stage 02 ยังส่ง `window` เป็น label เดียวแบบ exclusive อยู่ Stage 05 จะยังไม่ตรง paper แม้ feature count จะเท่ากับ 35/115/121 แล้วก็ตาม
