"""Stage 04 exploratory data analysis for temporal stroke prediction.

วัตถุประสงค์:
1) สรุปโครงข้อมูลและ class imbalance
2) วิเคราะห์ missingness/visit coverage/temporal coverage
3) สร้าง leakage audit summary
4) เตรียมหลักฐานเชิงข้อมูลสำหรับ Stage 05-08
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EDAConfig:
    records_path: Path = Path("output/data_cleaning_output/cleaned_pre_reference_records.csv")
    cohort_path: Path = Path("output/target_cohort_output/patient_level_cohort.csv")
    completeness_path: Path = Path("output/target_cohort_output/temporal_completeness_flags.csv")
    attrition_path: Path = Path("output/target_cohort_output/cohort_attrition_report.csv")
    output_dir: Path = Path("output/eda_output")
    patient_id_col: str = "patient_id"
    visit_date_col: str = "visit_date"
    reference_date_col: str = "reference_date"


NUMERIC_CLINICAL_COLUMNS = [
    "bps",
    "bpd",
    "hdl",
    "ldl",
    "fbs",
    "bmi",
    "egfr",
    "creatinine",
    "cholesterol",
    "triglyceride",
    "tc_hdl_ratio",
]

WINDOWS = ["FIRST", "MID", "LAST"]


def load_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def class_imbalance(cohort: pd.DataFrame) -> pd.DataFrame:
    """สรุปจำนวน stroke vs non-stroke ระดับผู้ป่วย."""
    counts = cohort["stroke"].value_counts(dropna=False).rename_axis("stroke").reset_index(name="patient_count")
    counts["label"] = counts["stroke"].map({0: "non_stroke", 1: "stroke"}).fillna("missing")
    counts["percent"] = counts["patient_count"] / counts["patient_count"].sum()
    return counts[["stroke", "label", "patient_count", "percent"]].sort_values("stroke")


def visit_frequency(records: pd.DataFrame, config: EDAConfig) -> pd.DataFrame:
    """สรุปจำนวน visit และช่วงเวลาติดตามต่อผู้ป่วย."""
    grouped = records.groupby(config.patient_id_col)[config.visit_date_col]
    summary = grouped.agg(["count", "min", "max"]).reset_index()
    summary = summary.rename(columns={"count": "visit_count", "min": "first_visit_date", "max": "last_visit_date"})
    summary["followup_days"] = (summary["last_visit_date"] - summary["first_visit_date"]).dt.days
    return summary


def visit_frequency_distribution(coverage: pd.DataFrame) -> pd.DataFrame:
    values = coverage["visit_count"]
    return pd.DataFrame(
        [
            {
                "patients": int(len(values)),
                "mean_visits": float(values.mean()) if len(values) else 0.0,
                "median_visits": float(values.median()) if len(values) else 0.0,
                "min_visits": int(values.min()) if len(values) else 0,
                "max_visits": int(values.max()) if len(values) else 0,
                "p25_visits": float(values.quantile(0.25)) if len(values) else 0.0,
                "p75_visits": float(values.quantile(0.75)) if len(values) else 0.0,
            }
        ]
    )


def window_visit_counts(records: pd.DataFrame, config: EDAConfig) -> pd.DataFrame:
    """นับจำนวน visit ต่อ patient ต่อ window."""
    if "window" not in records.columns:
        return pd.DataFrame()
    table = (
        records.dropna(subset=["window"])
        .groupby(["window", config.patient_id_col])
        .size()
        .rename("visit_count")
        .reset_index()
    )
    return table


def time_gap_summary(records: pd.DataFrame, config: EDAConfig) -> pd.DataFrame:
    """สรุปช่องว่างเวลา (days) ระหว่าง visit ต่อเนื่อง."""
    sorted_records = records.sort_values([config.patient_id_col, config.visit_date_col]).copy()
    sorted_records["days_since_previous_visit"] = (
        sorted_records.groupby(config.patient_id_col)[config.visit_date_col].diff().dt.days
    )
    gaps = sorted_records["days_since_previous_visit"].dropna()
    if gaps.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "gap_count": int(len(gaps)),
                "mean_days": float(gaps.mean()),
                "median_days": float(gaps.median()),
                "p25_days": float(gaps.quantile(0.25)),
                "p75_days": float(gaps.quantile(0.75)),
                "max_days": int(gaps.max()),
            }
        ]
    )


def missingness_by_variable(records: pd.DataFrame) -> pd.DataFrame:
    """สรุป missingness ต่อคอลัมน์."""
    rows = []
    for column in records.columns:
        rows.append(
            {
                "column": column,
                "missing_count": int(records[column].isna().sum()),
                "missing_percent": float(records[column].isna().mean()) if len(records) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["missing_percent", "missing_count"], ascending=False)


def missingness_by_group(records: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """สรุป missingness แยกตามกลุ่ม เช่น stroke/window."""
    if group_col not in records.columns:
        return pd.DataFrame()
    rows = []
    for group_value, group in records.groupby(group_col, dropna=False):
        for column in NUMERIC_CLINICAL_COLUMNS:
            if column not in group.columns:
                continue
            rows.append(
                {
                    group_col: group_value,
                    "column": column,
                    "records": int(len(group)),
                    "missing_count": int(group[column].isna().sum()),
                    "missing_percent": float(group[column].isna().mean()) if len(group) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def temporal_coverage(completeness: pd.DataFrame, attrition: pd.DataFrame | None = None) -> pd.DataFrame:
    """สรุปความครอบคลุมของ FIRST/MID/LAST และผล attrition."""
    rows = []
    if completeness.empty:
        return pd.DataFrame()
    total = len(completeness)
    complete = int(completeness["temporal_complete"].sum()) if "temporal_complete" in completeness.columns else 0
    rows.append(
        {
            "metric": "patients_with_temporal_completeness_row",
            "patient_count": total,
            "percent": 1.0,
        }
    )
    rows.append(
        {
            "metric": "temporal_complete_patients",
            "patient_count": complete,
            "percent": complete / total if total else 0.0,
        }
    )
    for window in WINDOWS:
        col = f"{window.lower()}_has_visit"
        if col in completeness.columns:
            count = int(completeness[col].sum())
            rows.append({"metric": f"{window.lower()}_has_visit", "patient_count": count, "percent": count / total})
    if attrition is not None and not attrition.empty:
        final = attrition.tail(1).iloc[0].to_dict()
        rows.append(
            {
                "metric": f"attrition_final_step_{final.get('step', '')}",
                "patient_count": int(final.get("patients_remaining", 0)),
                "percent": np.nan,
            }
        )
    return pd.DataFrame(rows)


def clinical_descriptive_stats(records: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ descriptive stats ของตัวแปรคลินิกทั้งรวมและแยก stroke."""
    rows = []
    group_cols = ["stroke"] if "stroke" in records.columns else []
    for column in NUMERIC_CLINICAL_COLUMNS:
        if column not in records.columns:
            continue
        if group_cols:
            grouped = records.groupby("stroke")[column]
            for stroke_value, series in grouped:
                rows.append(_describe_series(column, series, stroke_value))
        rows.append(_describe_series(column, records[column], "all"))
    return pd.DataFrame(rows)


def _describe_series(column: str, series: pd.Series, stroke_value: object) -> dict[str, object]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return {
        "column": column,
        "stroke": stroke_value,
        "count": int(numeric.count()),
        "mean": float(numeric.mean()) if len(numeric) else np.nan,
        "std": float(numeric.std()) if len(numeric) > 1 else np.nan,
        "min": float(numeric.min()) if len(numeric) else np.nan,
        "p25": float(numeric.quantile(0.25)) if len(numeric) else np.nan,
        "median": float(numeric.median()) if len(numeric) else np.nan,
        "p75": float(numeric.quantile(0.75)) if len(numeric) else np.nan,
        "max": float(numeric.max()) if len(numeric) else np.nan,
    }


def leakage_audit(records: pd.DataFrame, config: EDAConfig) -> pd.DataFrame:
    """ตรวจหลักฐานว่ามี/ไม่มี post-reference records."""
    rows = []
    if config.visit_date_col in records.columns and config.reference_date_col in records.columns:
        valid = records[[config.visit_date_col, config.reference_date_col]].dropna()
        post_ref = valid[config.visit_date_col] > valid[config.reference_date_col]
        rows.append(
            {
                "check": "no_post_reference_records",
                "passed": bool(~post_ref.any()),
                "failed_record_count": int(post_ref.sum()),
            }
        )
    else:
        rows.append(
            {
                "check": "no_post_reference_records",
                "passed": False,
                "failed_record_count": None,
            }
        )
    return pd.DataFrame(rows)


def high_missing_variables(missingness: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    return missingness[missingness["missing_percent"] >= threshold].copy()


def build_report_markdown(report: dict[str, object], config: EDAConfig) -> str:
    return f"""# EDA Summary Report

## Summary

- Records input: `{config.records_path}`
- Cohort input: `{config.cohort_path}`
- Records: {report["records"]:,}
- Patients: {report["patients"]:,}
- Stroke patients: {report["stroke_patients"]:,}
- Non-stroke patients: {report["nonstroke_patients"]:,}
- Stroke prevalence: {report["stroke_prevalence"]:.4f}
- Temporal-complete patients: {report["temporal_complete_patients"]:,}
- High-missing variables at >=50%: {report["high_missing_variable_count"]:,}
- Leakage audit passed: `{report["leakage_audit_passed"]}`

## Key Note

Strict FIRST/MID/LAST completeness leaves very few temporal-complete patients in the current data. Stage 05 should keep the paper default windows as baseline, but also consider sensitivity analysis with alternative windows such as 90/180 days.

## Outputs

- `class_imbalance.csv`
- `visit_frequency_by_patient.csv`
- `visit_frequency_distribution.csv`
- `window_visit_counts.csv`
- `time_gap_summary.csv`
- `missingness_by_variable.csv`
- `missingness_by_stroke.csv`
- `missingness_by_window.csv`
- `temporal_coverage_summary.csv`
- `clinical_descriptive_stats.csv`
- `high_missing_variables.csv`
- `leakage_audit_summary.csv`
- `eda_summary_report.json`
- `eda_summary_report.md`
"""


def run_eda(config: EDAConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 04."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    records = load_csv(config.records_path, parse_dates=[config.visit_date_col, config.reference_date_col])
    cohort = load_csv(config.cohort_path)
    completeness = load_csv(config.completeness_path) if config.completeness_path.exists() else pd.DataFrame()
    attrition = load_csv(config.attrition_path) if config.attrition_path.exists() else pd.DataFrame()

    imbalance = class_imbalance(cohort)
    visit_cov = visit_frequency(records, config)
    visit_dist = visit_frequency_distribution(visit_cov)
    window_counts = window_visit_counts(records, config)
    gap_summary = time_gap_summary(records, config)
    missing_variable = missingness_by_variable(records)
    missing_stroke = missingness_by_group(records, "stroke")
    missing_window = missingness_by_group(records, "window")
    temporal_cov = temporal_coverage(completeness, attrition)
    clinical_stats = clinical_descriptive_stats(records)
    leakage = leakage_audit(records, config)
    high_missing = high_missing_variables(missing_variable)

    stroke_row = imbalance[imbalance["stroke"] == 1]
    nonstroke_row = imbalance[imbalance["stroke"] == 0]
    stroke_patients = int(stroke_row["patient_count"].sum()) if not stroke_row.empty else 0
    nonstroke_patients = int(nonstroke_row["patient_count"].sum()) if not nonstroke_row.empty else 0
    patients = int(cohort[config.patient_id_col if config.patient_id_col in cohort.columns else "hn"].nunique())
    report = {
        "records": int(len(records)),
        "patients": patients,
        "stroke_patients": stroke_patients,
        "nonstroke_patients": nonstroke_patients,
        "stroke_prevalence": stroke_patients / patients if patients else 0.0,
        "temporal_complete_patients": int(completeness["temporal_complete"].sum())
        if "temporal_complete" in completeness.columns
        else 0,
        "high_missing_variable_count": int(len(high_missing)),
        "leakage_audit_passed": bool(leakage["passed"].all()) if "passed" in leakage.columns else False,
    }

    write_csv(imbalance, config.output_dir / "class_imbalance.csv")
    write_csv(visit_cov, config.output_dir / "visit_frequency_by_patient.csv")
    write_csv(visit_dist, config.output_dir / "visit_frequency_distribution.csv")
    write_csv(window_counts, config.output_dir / "window_visit_counts.csv")
    write_csv(gap_summary, config.output_dir / "time_gap_summary.csv")
    write_csv(missing_variable, config.output_dir / "missingness_by_variable.csv")
    write_csv(missing_stroke, config.output_dir / "missingness_by_stroke.csv")
    write_csv(missing_window, config.output_dir / "missingness_by_window.csv")
    write_csv(temporal_cov, config.output_dir / "temporal_coverage_summary.csv")
    write_csv(clinical_stats, config.output_dir / "clinical_descriptive_stats.csv")
    write_csv(high_missing, config.output_dir / "high_missing_variables.csv")
    write_csv(leakage, config.output_dir / "leakage_audit_summary.csv")
    write_json(report, config.output_dir / "eda_summary_report.json")
    (config.output_dir / "eda_summary_report.md").write_text(build_report_markdown(report, config), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 04 EDA.")
    parser.add_argument("--records-path", default=str(EDAConfig.records_path))
    parser.add_argument("--cohort-path", default=str(EDAConfig.cohort_path))
    parser.add_argument("--completeness-path", default=str(EDAConfig.completeness_path))
    parser.add_argument("--attrition-path", default=str(EDAConfig.attrition_path))
    parser.add_argument("--output-dir", default=str(EDAConfig.output_dir))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = EDAConfig(
        records_path=Path(args.records_path),
        cohort_path=Path(args.cohort_path),
        completeness_path=Path(args.completeness_path),
        attrition_path=Path(args.attrition_path),
        output_dir=Path(args.output_dir),
    )
    report = run_eda(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
