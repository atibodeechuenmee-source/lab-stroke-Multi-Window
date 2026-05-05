# Data Cleaning Report

- Run at: 2026-05-05T14:32:04
- Raw data: `data\raw\patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Cleaned data: `data\interim\cleaned_stroke_records.csv`
- Raw rows: 218,772
- Cleaned rows: 202,331
- Rows removed: 16,441
- Raw positive records: 5170
- Cleaned positive records: 4349

## Rules

- imputation: not_applied_to_avoid_train_test_leakage
- scaling: not_applied_to_avoid_train_test_leakage
- encoding: not_applied_to_avoid_train_test_leakage
- outlier_policy: fixed_clinical_ranges_set_impossible_values_to_missing
- duplicate_policy: drop_exact_duplicates_then_patient_visit_diagnosis_duplicates

## Missing Indicators

- `bps_missing_indicator`
- `bpd_missing_indicator`
- `HDL_missing_indicator`
- `LDL_missing_indicator`
- `Triglyceride_missing_indicator`
- `Cholesterol_missing_indicator`
- `FBS_missing_indicator`
- `eGFR_missing_indicator`
- `Creatinine_missing_indicator`
- `TC:HDL_ratio_missing_indicator`

## Outputs

- cleaned_dataset: `data\interim\cleaned_stroke_records.csv`
- cleaning_log: `output\data_cleaning_output\cleaning_log.csv`
- missing_summary_after_cleaning: `output\data_cleaning_output\missing_summary_after_cleaning.csv`
- range_summary_after_cleaning: `output\data_cleaning_output\range_summary_after_cleaning.csv`
- cleaning_report_json: `output\data_cleaning_output\cleaning_report.json`
- cleaning_report_md: `output\data_cleaning_output\cleaning_report.md`
