# Stage 05: Feature Engineering

## Purpose

สร้าง feature table ระดับ patient สำหรับเปรียบเทียบ single-shot baseline กับ temporal feature models ตาม Extract Set 1/2/3 ของ paper

## Input

- Cleaned pre-reference records จาก Stage 03
- Patient-level cohort และ window assignment จาก Stage 02
- EDA findings จาก Stage 04

## Process

1. Single-shot baseline:
   - เลือก latest pre-reference record ต่อ patient
   - สร้าง baseline features จาก record ล่าสุดเท่านั้น
   - ใช้เป็น comparator หลักของ temporal models
2. Temporal windows:
   - FIRST: 21-9 เดือนก่อน reference date
   - MID: 18-6 เดือนก่อน reference date
   - LAST: 15-3 เดือนก่อน reference date
3. Core numerical variables:
   - BPS, BPD, HDL, LDL, FBS, BMI, eGFR, creatinine, total cholesterol, triglycerides
4. Extract Set 1:
   - core demographic และ clinical variables across windows
   - categorical features เช่น sex, AF, smoking, drinking
5. Extract Set 2:
   - เพิ่ม statistical descriptors: mean, min, max, standard deviation, first, last
   - เพิ่ม temporal descriptors: delta, slope, cross-window min/max differences, measurement count differences
6. Extract Set 3:
   - เพิ่ม diabetes, hypertension, heart disease, statin flag, antihypertensive flag, `TC:HDL`
7. คำนวณ derived biomarker:

```text
TC:HDL = Total Cholesterol / HDL
```

8. คำนวณ temporal descriptors:

```text
Delta(X) = X_LAST - X_FIRST
Slope(X) = (X_LAST - X_FIRST) / (t_LAST - t_FIRST)
```

## Output

- Single-shot baseline feature table
- Extract Set 1 feature table
- Extract Set 2 feature table
- Extract Set 3 feature table
- Feature dictionary
- Feature generation log
- Exclusion report สำหรับ patient ที่สร้าง features ไม่ได้

## Checks / Acceptance Criteria

- Feature table ทุกชุดมีหนึ่งแถวต่อหนึ่ง patient
- ทุก features คำนวณจาก pre-reference records เท่านั้น
- Baseline features ใช้ latest pre-reference record ไม่ใช่ latest record หลัง event
- Temporal features ใช้เฉพาะ records ใน FIRST/MID/LAST
- `TC:HDL` ไม่หารด้วยศูนย์ และมี missing handling ชัดเจน
- Feature dictionary ระบุ source window และ aggregation method ของแต่ละ feature

## Relation to Paper

Stage นี้ implement แนวคิดสำคัญที่สุดของ paper คือการสร้าง temporal representations และ hierarchical feature sets เพื่อวัดว่าการเพิ่ม feature-engineering complexity ช่วย prediction มากขึ้นหรือไม่

