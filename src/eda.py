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
from typing import Any

import numpy as np
import pandas as pd


PAPER_REFERENCE = {
    "title": "Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction",
    "method_section": "Exploratory review before Feature Extraction",
    "eda_principle": "quantify irregular, incomplete, heterogeneous EHR before temporal modeling",
    "default_windows": ["FIRST", "MID", "LAST"],
}
MIN_TEMPORAL_COMPLETE_STROKE_CASES_FOR_MODELING = 2


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


def _json_ready(value: Any) -> Any:
    """แปลงค่า pandas/numpy ให้อยู่ในรูปที่เขียน JSON ได้."""
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def first_existing(columns: list[str] | pd.Index, candidates: list[str]) -> str | None:
    """หา column แรกที่มีอยู่จริง เพื่อรองรับทั้ง raw/stage-standardized naming."""
    existing = set(map(str, columns))
    for candidate in candidates:
        if candidate in existing:
            return candidate
    return None


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
            rows.append({"metric": f"{window.lower()}_has_visit", "patient_count": count, "percent": count / total if total else 0.0})
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


def window_coverage_by_label(records: pd.DataFrame, config: EDAConfig) -> pd.DataFrame:
    """สรุป records/patients ในแต่ละ temporal window แยก stroke/non-stroke."""
    if "window" not in records.columns or "stroke" not in records.columns:
        return pd.DataFrame()
    rows = []
    for window in WINDOWS:
        subset = records[records["window"] == window]
        row: dict[str, object] = {
            "window": window,
            "records": int(len(subset)),
            "patients": int(subset[config.patient_id_col].nunique()) if config.patient_id_col in subset.columns else 0,
        }
        for stroke_value, label in [(0, "nonstroke"), (1, "stroke")]:
            label_subset = subset[subset["stroke"] == stroke_value]
            row[f"{label}_records"] = int(len(label_subset))
            row[f"{label}_patients"] = (
                int(label_subset[config.patient_id_col].nunique())
                if config.patient_id_col in label_subset.columns
                else 0
            )
        rows.append(row)
    outside = records[records["window"].isna()] if "window" in records.columns else pd.DataFrame()
    rows.append(
        {
            "window": "OUTSIDE_WINDOWS",
            "records": int(len(outside)),
            "patients": int(outside[config.patient_id_col].nunique()) if config.patient_id_col in outside.columns else 0,
            "nonstroke_records": int((outside["stroke"] == 0).sum()) if "stroke" in outside.columns else 0,
            "nonstroke_patients": int(outside.loc[outside["stroke"] == 0, config.patient_id_col].nunique())
            if "stroke" in outside.columns and config.patient_id_col in outside.columns
            else 0,
            "stroke_records": int((outside["stroke"] == 1).sum()) if "stroke" in outside.columns else 0,
            "stroke_patients": int(outside.loc[outside["stroke"] == 1, config.patient_id_col].nunique())
            if "stroke" in outside.columns and config.patient_id_col in outside.columns
            else 0,
        }
    )
    return pd.DataFrame(rows)


def temporal_complete_case_summary(cohort: pd.DataFrame, completeness: pd.DataFrame) -> pd.DataFrame:
    """สรุปจำนวน stroke/non-stroke ใน temporal-complete cohort."""
    if completeness.empty or "temporal_complete" not in completeness.columns:
        return pd.DataFrame(
            [
                {
                    "group": "temporal_complete",
                    "patients": 0,
                    "stroke_patients": 0,
                    "nonstroke_patients": 0,
                    "stroke_prevalence": 0.0,
                }
            ]
        )
    cohort_id = first_existing(cohort.columns, ["patient_id", "hn"])
    completeness_id = first_existing(completeness.columns, ["patient_id", "hn"])
    if cohort_id is None or completeness_id is None or "stroke" not in cohort.columns:
        return pd.DataFrame()
    complete_ids = completeness.loc[completeness["temporal_complete"], completeness_id]
    complete = cohort[cohort[cohort_id].isin(complete_ids)].copy()
    stroke_patients = int((complete["stroke"] == 1).sum())
    nonstroke_patients = int((complete["stroke"] == 0).sum())
    patients = int(len(complete))
    return pd.DataFrame(
        [
            {
                "group": "all_patient_level_cohort",
                "patients": int(len(cohort)),
                "stroke_patients": int((cohort["stroke"] == 1).sum()),
                "nonstroke_patients": int((cohort["stroke"] == 0).sum()),
                "stroke_prevalence": float((cohort["stroke"] == 1).mean()) if len(cohort) else 0.0,
            },
            {
                "group": "temporal_complete",
                "patients": patients,
                "stroke_patients": stroke_patients,
                "nonstroke_patients": nonstroke_patients,
                "stroke_prevalence": stroke_patients / patients if patients else 0.0,
            },
        ]
    )


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


def build_sensitivity_recommendation(report: dict[str, object]) -> pd.DataFrame:
    """ประเมินว่าควรทำ sensitivity analysis ด้วย windows อื่นหรือไม่."""
    temporal_complete = int(report.get("temporal_complete_patients", 0) or 0)
    temporal_complete_stroke = int(report.get("temporal_complete_stroke_patients", 0) or 0)
    recommend = temporal_complete_stroke < MIN_TEMPORAL_COMPLETE_STROKE_CASES_FOR_MODELING
    return pd.DataFrame(
        [
            {
                "recommend_sensitivity_analysis": recommend,
                "reason": (
                    "strict FIRST/MID/LAST temporal-complete cohort has too few stroke cases for reliable modeling"
                    if recommend
                    else "strict FIRST/MID/LAST temporal-complete cohort has enough stroke cases for minimal modeling"
                ),
                "temporal_complete_patients": temporal_complete,
                "temporal_complete_stroke_patients": temporal_complete_stroke,
                "suggested_fallback_windows": "90/180 days as sensitivity analysis; keep paper windows as primary baseline",
            }
        ]
    )


def build_acceptance_checks(
    imbalance: pd.DataFrame,
    temporal_cov: pd.DataFrame,
    missing_window: pd.DataFrame,
    leakage: pd.DataFrame,
    report: dict[str, object],
    sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    """สร้าง acceptance checks ตาม docs/pipeline/04-eda.md."""
    has_stroke = bool((imbalance["stroke"] == 1).any()) if "stroke" in imbalance.columns else False
    has_nonstroke = bool((imbalance["stroke"] == 0).any()) if "stroke" in imbalance.columns else False
    temporal_complete_reported = bool(
        not temporal_cov.empty and (temporal_cov["metric"] == "temporal_complete_patients").any()
    )
    missing_windows = set(missing_window["window"].dropna().astype(str).unique()) if "window" in missing_window.columns else set()
    leakage_ok = bool(leakage["passed"].all()) if "passed" in leakage.columns else False
    enough_temporal_stroke = (
        int(report.get("temporal_complete_stroke_patients", 0) or 0)
        >= MIN_TEMPORAL_COMPLETE_STROKE_CASES_FOR_MODELING
    )
    sensitivity_recommended = bool(sensitivity.iloc[0]["recommend_sensitivity_analysis"]) if not sensitivity.empty else False
    return pd.DataFrame(
        [
            {
                "check": "class_imbalance_reported",
                "passed": has_stroke and has_nonstroke,
                "detail": f"stroke={report.get('stroke_patients')}; nonstroke={report.get('nonstroke_patients')}",
            },
            {
                "check": "temporal_complete_patient_count_reported",
                "passed": temporal_complete_reported,
                "detail": f"temporal_complete_patients={report.get('temporal_complete_patients')}",
            },
            {
                "check": "missingness_by_first_mid_last_reported",
                "passed": set(WINDOWS).issubset(missing_windows),
                "detail": f"windows_reported={sorted(missing_windows)}",
            },
            {
                "check": "no_post_reference_records_confirmed",
                "passed": leakage_ok,
                "detail": "; ".join(leakage.get("check", pd.Series(dtype=str)).astype(str).tolist()),
            },
            {
                "check": "strict_completeness_stroke_case_count_identified",
                "passed": "temporal_complete_stroke_patients" in report,
                "detail": f"temporal_complete_stroke_patients={report.get('temporal_complete_stroke_patients')}",
            },
            {
                "check": "sensitivity_analysis_recommended_if_needed",
                "passed": enough_temporal_stroke or sensitivity_recommended,
                "detail": f"enough_temporal_stroke={enough_temporal_stroke}; recommended={sensitivity_recommended}",
            },
        ]
    )


def build_report_markdown(report: dict[str, object], config: EDAConfig) -> str:
    checks_passed = report.get("acceptance_checks_passed", 0)
    checks_total = report.get("acceptance_checks_total", 0)
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
- Temporal-complete stroke patients: {report["temporal_complete_stroke_patients"]:,}
- High-missing variables at >=50%: {report["high_missing_variable_count"]:,}
- Leakage audit passed: `{report["leakage_audit_passed"]}`
- Sensitivity analysis recommended: `{report["sensitivity_analysis_recommended"]}`
- Acceptance checks passed: {checks_passed}/{checks_total}

## Paper Reference

- Paper: `{PAPER_REFERENCE["title"]}`
- Method context: `{PAPER_REFERENCE["method_section"]}`
- EDA principle: `{PAPER_REFERENCE["eda_principle"]}`

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
- `window_coverage_by_label.csv`
- `temporal_complete_case_summary.csv`
- `sensitivity_analysis_recommendation.csv`
- `clinical_descriptive_stats.csv`
- `high_missing_variables.csv`
- `leakage_audit_summary.csv`
- `eda_acceptance_checks.csv`
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
    window_label_cov = window_coverage_by_label(records, config)
    temporal_complete_cases = temporal_complete_case_summary(cohort, completeness)
    clinical_stats = clinical_descriptive_stats(records)
    leakage = leakage_audit(records, config)
    high_missing = high_missing_variables(missing_variable)

    stroke_row = imbalance[imbalance["stroke"] == 1]
    nonstroke_row = imbalance[imbalance["stroke"] == 0]
    stroke_patients = int(stroke_row["patient_count"].sum()) if not stroke_row.empty else 0
    nonstroke_patients = int(nonstroke_row["patient_count"].sum()) if not nonstroke_row.empty else 0
    patients = int(cohort[config.patient_id_col if config.patient_id_col in cohort.columns else "hn"].nunique())
    temporal_complete_row = (
        temporal_complete_cases[temporal_complete_cases["group"] == "temporal_complete"]
        if not temporal_complete_cases.empty and "group" in temporal_complete_cases.columns
        else pd.DataFrame()
    )
    temporal_complete_stroke = (
        int(temporal_complete_row["stroke_patients"].iloc[0]) if not temporal_complete_row.empty else 0
    )
    temporal_complete_nonstroke = (
        int(temporal_complete_row["nonstroke_patients"].iloc[0]) if not temporal_complete_row.empty else 0
    )
    report = {
        "paper_reference": PAPER_REFERENCE,
        "records": int(len(records)),
        "patients": patients,
        "stroke_patients": stroke_patients,
        "nonstroke_patients": nonstroke_patients,
        "stroke_prevalence": stroke_patients / patients if patients else 0.0,
        "temporal_complete_patients": int(completeness["temporal_complete"].sum())
        if "temporal_complete" in completeness.columns
        else 0,
        "temporal_complete_stroke_patients": temporal_complete_stroke,
        "temporal_complete_nonstroke_patients": temporal_complete_nonstroke,
        "high_missing_variable_count": int(len(high_missing)),
        "leakage_audit_passed": bool(leakage["passed"].all()) if "passed" in leakage.columns else False,
    }
    sensitivity = build_sensitivity_recommendation(report)
    acceptance_checks = build_acceptance_checks(
        imbalance,
        temporal_cov,
        missing_window,
        leakage,
        report,
        sensitivity,
    )
    report.update(
        {
            "sensitivity_analysis_recommended": bool(sensitivity.iloc[0]["recommend_sensitivity_analysis"])
            if not sensitivity.empty
            else False,
            "acceptance_checks_passed": int(acceptance_checks["passed"].sum()),
            "acceptance_checks_total": int(len(acceptance_checks)),
            "acceptance_passed": bool(acceptance_checks["passed"].all()),
        }
    )
    report = {key: _json_ready(value) for key, value in report.items()}

    write_csv(imbalance, config.output_dir / "class_imbalance.csv")
    write_csv(visit_cov, config.output_dir / "visit_frequency_by_patient.csv")
    write_csv(visit_dist, config.output_dir / "visit_frequency_distribution.csv")
    write_csv(window_counts, config.output_dir / "window_visit_counts.csv")
    write_csv(gap_summary, config.output_dir / "time_gap_summary.csv")
    write_csv(missing_variable, config.output_dir / "missingness_by_variable.csv")
    write_csv(missing_stroke, config.output_dir / "missingness_by_stroke.csv")
    write_csv(missing_window, config.output_dir / "missingness_by_window.csv")
    write_csv(temporal_cov, config.output_dir / "temporal_coverage_summary.csv")
    write_csv(window_label_cov, config.output_dir / "window_coverage_by_label.csv")
    write_csv(temporal_complete_cases, config.output_dir / "temporal_complete_case_summary.csv")
    write_csv(sensitivity, config.output_dir / "sensitivity_analysis_recommendation.csv")
    write_csv(clinical_stats, config.output_dir / "clinical_descriptive_stats.csv")
    write_csv(high_missing, config.output_dir / "high_missing_variables.csv")
    write_csv(leakage, config.output_dir / "leakage_audit_summary.csv")
    write_csv(acceptance_checks, config.output_dir / "eda_acceptance_checks.csv")
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
