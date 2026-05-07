"""Stage 02 target and cohort construction.

Implements docs/pipeline/02-target-and-cohort.md. The stage builds
patient-level stroke labels, reference dates, pre-reference records,
temporal window assignments, completeness flags, and attrition reports.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


STROKE_PATTERN = re.compile(r"\bI6[0-8](?:\.\d+)?\b", re.IGNORECASE)

WINDOWS = {
    "FIRST": (21.0, 9.0),
    "MID": (18.0, 6.0),
    "LAST": (15.0, 3.0),
}

CORE_CLINICAL_COLUMNS = [
    "bps",
    "bpd",
    "HDL",
    "LDL",
    "FBS",
    "bmi",
    "eGFR",
    "Creatinine",
    "Cholesterol",
    "Triglyceride",
]


@dataclass(frozen=True)
class TargetCohortConfig:
    input_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/target_cohort_output")
    patient_id_col: str = "hn"
    visit_date_col: str = "vstdate"
    principal_dx_col: str = "PrincipleDiagnosis"
    comorbidity_dx_col: str = "ComorbidityDiagnosis"
    months_per_day: float = 30.4375


def load_records(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input file type: {path}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _stroke_mask(df: pd.DataFrame, diagnosis_cols: list[str]) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for column in diagnosis_cols:
        if column in df.columns:
            mask = mask | df[column].astype(str).str.contains(STROKE_PATTERN, na=False)
    return mask


def validate_required_columns(df: pd.DataFrame, config: TargetCohortConfig) -> None:
    required = [config.patient_id_col, config.visit_date_col]
    diagnosis = [config.principal_dx_col, config.comorbidity_dx_col]
    missing_required = [column for column in required if column not in df.columns]
    missing_diagnosis = [column for column in diagnosis if column not in df.columns]
    if missing_required:
        raise KeyError(f"Missing required columns: {missing_required}")
    if len(missing_diagnosis) == len(diagnosis):
        raise KeyError(f"Missing all diagnosis columns: {missing_diagnosis}")


def prepare_records(df: pd.DataFrame, config: TargetCohortConfig) -> pd.DataFrame:
    validate_required_columns(df, config)
    prepared = df.copy()
    prepared[config.visit_date_col] = pd.to_datetime(prepared[config.visit_date_col], errors="coerce")
    prepared = prepared.dropna(subset=[config.patient_id_col, config.visit_date_col])
    prepared = prepared.drop_duplicates()
    for column in CORE_CLINICAL_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    return prepared


def build_patient_cohort(records: pd.DataFrame, config: TargetCohortConfig) -> pd.DataFrame:
    diagnosis_cols = [config.principal_dx_col, config.comorbidity_dx_col]
    working = records.copy()
    working["is_stroke_event"] = _stroke_mask(working, diagnosis_cols)

    first_stroke = (
        working.loc[working["is_stroke_event"]]
        .groupby(config.patient_id_col)[config.visit_date_col]
        .min()
        .rename("first_stroke_date")
    )
    last_visit = working.groupby(config.patient_id_col)[config.visit_date_col].max().rename("last_visit_date")
    first_visit = working.groupby(config.patient_id_col)[config.visit_date_col].min().rename("first_visit_date")
    record_count = working.groupby(config.patient_id_col).size().rename("record_count")

    cohort = pd.concat([first_visit, last_visit, record_count, first_stroke], axis=1).reset_index()
    cohort["stroke"] = cohort["first_stroke_date"].notna().astype(int)
    cohort["reference_date"] = cohort["first_stroke_date"].fillna(cohort["last_visit_date"])
    cohort["reference_rule"] = cohort["stroke"].map({1: "first_stroke_date", 0: "last_visit_date"})
    return cohort


def assign_windows(months_before_reference: pd.Series) -> pd.Series:
    labels = pd.Series(pd.NA, index=months_before_reference.index, dtype="object")
    for window_name, (upper_month, lower_month) in WINDOWS.items():
        labels.loc[months_before_reference.between(lower_month, upper_month, inclusive="both")] = window_name
    return labels


def build_pre_reference_records(
    records: pd.DataFrame, cohort: pd.DataFrame, config: TargetCohortConfig
) -> pd.DataFrame:
    merged = records.merge(
        cohort[[config.patient_id_col, "stroke", "reference_date", "reference_rule"]],
        on=config.patient_id_col,
        how="inner",
    )
    pre_reference = merged[merged[config.visit_date_col] <= merged["reference_date"]].copy()
    pre_reference["days_before_reference"] = (
        pre_reference["reference_date"] - pre_reference[config.visit_date_col]
    ).dt.days
    pre_reference["months_before_reference"] = pre_reference["days_before_reference"] / config.months_per_day
    pre_reference["window"] = assign_windows(pre_reference["months_before_reference"])
    return pre_reference


def build_temporal_completeness(pre_reference: pd.DataFrame, config: TargetCohortConfig) -> pd.DataFrame:
    available_core = [column for column in CORE_CLINICAL_COLUMNS if column in pre_reference.columns]
    rows: list[dict[str, object]] = []
    patients = pre_reference[config.patient_id_col].dropna().drop_duplicates()

    for patient_id in patients:
        patient_records = pre_reference[pre_reference[config.patient_id_col] == patient_id]
        row: dict[str, object] = {config.patient_id_col: patient_id}
        temporal_complete = True
        for window_name in WINDOWS:
            window_records = patient_records[patient_records["window"] == window_name]
            has_visit = len(window_records) > 0
            has_core = bool(available_core) and all(window_records[column].notna().any() for column in available_core)
            row[f"{window_name.lower()}_visit_count"] = int(len(window_records))
            row[f"{window_name.lower()}_has_visit"] = has_visit
            row[f"{window_name.lower()}_has_core_clinical"] = has_core
            temporal_complete = temporal_complete and has_visit and has_core
        row["core_clinical_columns_checked"] = ",".join(available_core)
        row["temporal_complete"] = temporal_complete
        rows.append(row)

    return pd.DataFrame(rows)


def build_attrition_report(
    records: pd.DataFrame,
    prepared: pd.DataFrame,
    cohort: pd.DataFrame,
    pre_reference: pd.DataFrame,
    completeness: pd.DataFrame,
    config: TargetCohortConfig,
) -> pd.DataFrame:
    initial_patients = records[config.patient_id_col].nunique() if config.patient_id_col in records.columns else 0
    prepared_patients = prepared[config.patient_id_col].nunique()
    post_reference_removed = len(prepared) - len(pre_reference)
    window_patient_count = pre_reference.loc[pre_reference["window"].notna(), config.patient_id_col].nunique()
    complete_patients = int(completeness["temporal_complete"].sum()) if not completeness.empty else 0

    rows = [
        {
            "step": "raw_input",
            "patients_remaining": int(initial_patients),
            "records_remaining": int(len(records)),
            "patients_removed_at_step": 0,
            "records_removed_at_step": 0,
            "reason": "Raw input before Stage 02 filtering",
        },
        {
            "step": "valid_patient_and_visit_date",
            "patients_remaining": int(prepared_patients),
            "records_remaining": int(len(prepared)),
            "patients_removed_at_step": int(initial_patients - prepared_patients),
            "records_removed_at_step": int(len(records) - len(prepared)),
            "reason": "Drop rows without patient id or valid visit date and exact duplicates",
        },
        {
            "step": "pre_reference_records_only",
            "patients_remaining": int(pre_reference[config.patient_id_col].nunique()),
            "records_remaining": int(len(pre_reference)),
            "patients_removed_at_step": 0,
            "records_removed_at_step": int(post_reference_removed),
            "reason": "Remove records after reference date to prevent leakage",
        },
        {
            "step": "has_any_temporal_window_record",
            "patients_remaining": int(window_patient_count),
            "records_remaining": int(pre_reference["window"].notna().sum()),
            "patients_removed_at_step": int(pre_reference[config.patient_id_col].nunique() - window_patient_count),
            "records_removed_at_step": int(pre_reference["window"].isna().sum()),
            "reason": "Keep records assigned to FIRST/MID/LAST windows",
        },
        {
            "step": "temporal_complete",
            "patients_remaining": complete_patients,
            "records_remaining": int(
                pre_reference[pre_reference[config.patient_id_col].isin(
                    completeness.loc[completeness["temporal_complete"], config.patient_id_col]
                    if not completeness.empty
                    else []
                )].shape[0]
            ),
            "patients_removed_at_step": int(window_patient_count - complete_patients),
            "records_removed_at_step": 0,
            "reason": "Require visit and core clinical coverage in FIRST, MID, LAST",
        },
    ]
    return pd.DataFrame(rows)


def build_quality_checks(
    cohort: pd.DataFrame, pre_reference: pd.DataFrame, completeness: pd.DataFrame, config: TargetCohortConfig
) -> dict[str, object]:
    no_post_reference = bool((pre_reference[config.visit_date_col] <= pre_reference["reference_date"]).all())
    stroke_reference_ok = bool(
        cohort.loc[cohort["stroke"] == 1, "first_stroke_date"].eq(
            cohort.loc[cohort["stroke"] == 1, "reference_date"]
        ).all()
    )
    nonstroke_reference_ok = bool(
        cohort.loc[cohort["stroke"] == 0, "last_visit_date"].eq(
            cohort.loc[cohort["stroke"] == 0, "reference_date"]
        ).all()
    )
    return {
        "no_post_reference_records": no_post_reference,
        "stroke_reference_is_first_stroke_date": stroke_reference_ok,
        "nonstroke_reference_is_last_visit_date": nonstroke_reference_ok,
        "patients": int(len(cohort)),
        "stroke_patients": int(cohort["stroke"].sum()),
        "nonstroke_patients": int((cohort["stroke"] == 0).sum()),
        "pre_reference_records": int(len(pre_reference)),
        "temporal_complete_patients": int(completeness["temporal_complete"].sum()) if not completeness.empty else 0,
    }


def build_markdown_report(report: dict[str, object], config: TargetCohortConfig) -> str:
    return f"""# Target and Cohort Report

## Summary

- Input: `{config.input_path}`
- Patients: {report["patients"]:,}
- Stroke patients: {report["stroke_patients"]:,}
- Non-stroke patients: {report["nonstroke_patients"]:,}
- Pre-reference records: {report["pre_reference_records"]:,}
- Temporal-complete patients: {report["temporal_complete_patients"]:,}

## Reference Date Rules

- Stroke patient: first stroke event date from ICD-10 `I60-I68`
- Non-stroke patient: last clinical visit date
- All records after reference date are removed before window assignment

## Temporal Windows

- FIRST: 21-9 months before reference date
- MID: 18-6 months before reference date
- LAST: 15-3 months before reference date

## Quality Checks

- No post-reference records: `{report["no_post_reference_records"]}`
- Stroke reference is first stroke date: `{report["stroke_reference_is_first_stroke_date"]}`
- Non-stroke reference is last visit date: `{report["nonstroke_reference_is_last_visit_date"]}`

## Outputs

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `cohort_attrition_report.csv`
- `target_cohort_summary.json`
- `target_cohort_report.md`
"""


def run_target_cohort(config: TargetCohortConfig) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(config.input_path)
    prepared = prepare_records(records, config)
    cohort = build_patient_cohort(prepared, config)
    pre_reference = build_pre_reference_records(prepared, cohort, config)
    completeness = build_temporal_completeness(pre_reference, config)
    attrition = build_attrition_report(records, prepared, cohort, pre_reference, completeness, config)
    report = build_quality_checks(cohort, pre_reference, completeness, config)

    write_csv(cohort, config.output_dir / "patient_level_cohort.csv")
    write_csv(pre_reference, config.output_dir / "pre_reference_records_with_windows.csv")
    write_csv(completeness, config.output_dir / "temporal_completeness_flags.csv")
    write_csv(attrition, config.output_dir / "cohort_attrition_report.csv")
    write_json(report, config.output_dir / "target_cohort_summary.json")
    (config.output_dir / "target_cohort_report.md").write_text(
        build_markdown_report(report, config), encoding="utf-8"
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 02 target and cohort construction.")
    parser.add_argument("--input-path", default=str(TargetCohortConfig.input_path), help="Raw or cleaned EHR file.")
    parser.add_argument("--output-dir", default=str(TargetCohortConfig.output_dir), help="Output directory.")
    parser.add_argument("--patient-id-col", default=TargetCohortConfig.patient_id_col)
    parser.add_argument("--visit-date-col", default=TargetCohortConfig.visit_date_col)
    parser.add_argument("--principal-dx-col", default=TargetCohortConfig.principal_dx_col)
    parser.add_argument("--comorbidity-dx-col", default=TargetCohortConfig.comorbidity_dx_col)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TargetCohortConfig(
        input_path=Path(args.input_path),
        output_dir=Path(args.output_dir),
        patient_id_col=args.patient_id_col,
        visit_date_col=args.visit_date_col,
        principal_dx_col=args.principal_dx_col,
        comorbidity_dx_col=args.comorbidity_dx_col,
    )
    report = run_target_cohort(config)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

