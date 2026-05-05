# Target & Cohort Report

- Run at: 2026-05-05T14:22:25
- Raw data: `data\raw\patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- Stroke definition: `PrincipleDiagnosis ICD-10 I60-I69*`
- Horizon days: 90

## Record-Level Target

- record_count: 218772
- valid_patient_record_count: 218772
- invalid_patient_record_count: 0
- positive_record_count: 5170
- negative_record_count: 213602
- record_level_prevalence_percent: 2.36
- invalid_vstdate_count: 0
- missing_hn_count: 0

## Patient-Level 90-Day Cohort

- patient_cohort_count: 13031
- positive_patient_count: 406
- negative_patient_count: 12625
- patient_level_prevalence_percent: 3.12
- excluded_patient_count: 604

## Exclusions

- positive_outside_horizon: 604

## Outputs

- record_level_target: `output\target_cohort_output\record_level_target.csv`
- patient_level_cohort: `output\target_cohort_output\patient_level_90d_cohort.csv`
- exclusion_summary: `output\target_cohort_output\patient_level_90d_exclusions.csv`
- cohort_summary: `output\target_cohort_output\target_cohort_summary.json`
- report: `output\target_cohort_output\target_cohort_report.md`
