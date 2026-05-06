# Raw Data Audit Report

## Summary

- Raw file: `data\raw\patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Rows: 218,772
- Columns: 30
- Patients: 13,635
- Visit date range: 2014-10-01 to 2024-06-30
- Required fields available: 29
- Required fields missing: 0
- Stroke ICD `I60-I68` record hits: 3,950
- Visit coverage: records per patient median = 10.0, max = 137

## Outputs

- `raw_column_list.csv`
- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `raw_range_summary.csv`
- `visit_coverage_summary.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_report.json`
- `raw_data_report.md`

## Acceptance Criteria

- Patient identifier found: `True`
- Visit date found: `True`
- Principal diagnosis found: `True`
- Comorbidity diagnosis found: `True`
- Raw data was read-only: `true`

## Notes

Stage 01 does not clean, drop, overwrite, or mutate the raw source file. It only produces audit artifacts for the later cleaning and cohort-construction stages.
