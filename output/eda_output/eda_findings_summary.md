# EDA Findings Summary

- Run at: 2026-05-05T14:49:26
- Input: `data\raw\patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Rows: 218,772
- Columns: 31
- Numeric features: 25
- Primary modeling target: `stroke_3m` (patient-level)
- Patient cohort: 13,031
- Stroke positive patients: 406
- Patient-level stroke prevalence: 3.12%
- Record-level stroke event marker records: 5,170
- Record-level event marker prevalence: 2.36%

## High Missing Features

- `FBS`: 74.14%
- `Triglyceride`: 71.99%
- `LDL`: 70.93%
- `TC:HDL_ratio`: 70.87%
- `HDL`: 70.4%
- `Cholesterol`: 70.08%
- `eGFR`: 67.12%
- `Creatinine`: 64.84%

## Leakage Risk Columns

- `PrincipleDiagnosis`
- `ComorbidityDiagnosis`
- `ยาที่ได้รับ`
- `ตำบล`

## Checks

- EDA outputs are descriptive.
- Any preprocessing rule used for modeling should be checked again on train folds only.
- `TC:HDL_ratio` is a derived feature from cholesterol and HDL.
