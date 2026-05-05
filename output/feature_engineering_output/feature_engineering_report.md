# Feature Engineering Report

- Run at: 2026-05-05T15:03:53
- Source: `data\interim\cleaned_stroke_records.csv`
- Feature table: `data\processed\patient_level_90d_stroke.csv`
- Horizon days: 90
- Patient rows: 13,031
- Positive patients: 406
- Negative patients: 12,625
- Prevalence: 3.12%
- Model features: 88
- Excluded patients: 604

## Checks

- Features use only history at or before index_date.
- Diagnosis/text leakage columns are not model features.
- Target is patient-level `stroke_3m`.

## Outputs

- feature_table: `data\processed\patient_level_90d_stroke.csv`
- feature_list: `output\feature_engineering_output\feature_list.csv`
- feature_generation_log: `output\feature_engineering_output\feature_generation_log.csv`
- feature_engineering_report_json: `output\feature_engineering_output\feature_engineering_report.json`
- feature_engineering_report_md: `output\feature_engineering_output\feature_engineering_report.md`
- exclusions: `output\feature_engineering_output\feature_engineering_exclusions.csv`
