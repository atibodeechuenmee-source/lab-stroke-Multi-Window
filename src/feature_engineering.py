from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


STROKE_PATTERN = re.compile(r"^I6[0-9][0-9A-Z]*$", re.IGNORECASE)


@dataclass(frozen=True)
class Config:
    input_path: Path = Path("data/interim/cleaned_stroke_records.csv")
    fallback_input_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_path: Path = Path("data/processed/patient_level_90d_stroke.csv")
    output_dir: Path = Path("output/feature_engineering_output")
    horizon_days: int = 90


LATEST_FEATURES = [
    "sex",
    "age",
    "height",
    "bw",
    "bmi",
    "smoke",
    "drinking",
    "AF",
    "heart_disease",
    "hypertension",
    "diabetes",
    "Statin",
    "Gemfibrozil",
    "Antihypertensive_flag",
]

TEMPORAL_FEATURES = [
    "bps",
    "bpd",
    "HDL",
    "LDL",
    "Triglyceride",
    "Cholesterol",
    "FBS",
    "eGFR",
    "Creatinine",
    "TC:HDL_ratio",
]

LEAKAGE_COLUMNS = ["PrincipleDiagnosis", "ComorbidityDiagnosis", "ตำบล", "ยาที่ได้รับ"]
TARGET_AND_ID_COLUMNS = {"hn", "index_date", "event_date", "days_to_event", "stroke_3m"}


def load_source_data(config: Config) -> tuple[pd.DataFrame, Path]:
    input_path = config.input_path if config.input_path.exists() else config.fallback_input_path
    if not input_path.exists():
        raise FileNotFoundError(f"No feature engineering input found: {config.input_path} or {config.fallback_input_path}")

    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        df = pd.read_excel(input_path)

    required = {"hn", "vstdate", "PrincipleDiagnosis"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Missing required columns for feature engineering: {', '.join(missing)}")

    df["vstdate"] = pd.to_datetime(df["vstdate"], errors="coerce")
    df = df.dropna(subset=["hn", "vstdate"]).copy()
    df["stroke_event"] = build_stroke_event(df)
    df = df.sort_values(["hn", "vstdate"]).reset_index(drop=True)
    return df, input_path


def build_stroke_event(df: pd.DataFrame) -> pd.Series:
    diagnosis = df["PrincipleDiagnosis"].astype("string").str.strip().fillna("")
    return diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def choose_index_record(group: pd.DataFrame, max_date: pd.Timestamp, horizon_days: int):
    group = group.sort_values("vstdate")
    stroke_rows = group[group["stroke_event"] == 1]

    if not stroke_rows.empty:
        event_date = stroke_rows["vstdate"].min()
        prior_rows = group[group["vstdate"] < event_date]
        if prior_rows.empty:
            return None, "positive_no_prior_visit"

        index_row = prior_rows.iloc[-1]
        days_to_event = int((event_date - index_row["vstdate"]).days)
        if 1 <= days_to_event <= horizon_days:
            return (
                {
                    "hn": index_row["hn"],
                    "index_date": index_row["vstdate"],
                    "event_date": event_date,
                    "days_to_event": days_to_event,
                    "stroke_3m": 1,
                },
                "included_positive_within_horizon",
            )
        return None, "positive_outside_horizon"

    eligible = group[group["vstdate"] <= max_date - pd.Timedelta(days=horizon_days)]
    if eligible.empty:
        return None, "negative_insufficient_followup"

    index_row = eligible.iloc[-1]
    return (
        {
            "hn": index_row["hn"],
            "index_date": index_row["vstdate"],
            "event_date": pd.NaT,
            "days_to_event": pd.NA,
            "stroke_3m": 0,
        },
        "included_negative",
    )


def make_feature_row(history: pd.DataFrame, cohort_row: dict) -> dict:
    row = {
        "hn": cohort_row["hn"],
        "index_date": cohort_row["index_date"],
        "event_date": cohort_row["event_date"],
        "days_to_event": cohort_row["days_to_event"],
        "stroke_3m": cohort_row["stroke_3m"],
        "history_visit_count": len(history),
        "history_days_observed": int((history["vstdate"].max() - history["vstdate"].min()).days),
    }

    latest = history.iloc[-1]
    row["index_year"] = cohort_row["index_date"].year
    row["index_month"] = cohort_row["index_date"].month

    for column in LATEST_FEATURES:
        if column in history.columns:
            row[f"{column}_latest"] = latest[column]

    for column in TEMPORAL_FEATURES:
        if column not in history.columns:
            continue
        values = history[column]
        row[f"{column}_latest"] = values.iloc[-1]
        row[f"{column}_mean"] = values.mean()
        row[f"{column}_min"] = values.min()
        row[f"{column}_max"] = values.max()
        row[f"{column}_std"] = values.std()
        row[f"{column}_count"] = int(values.notna().sum())
        row[f"{column}_missing_rate"] = float(values.isna().mean())

    return row


def build_feature_table(df: pd.DataFrame, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_date = df["vstdate"].max()
    rows = []
    exclusion_records = []

    for hn, group in df.groupby("hn", sort=False):
        cohort_row, reason = choose_index_record(group, max_date, config.horizon_days)
        if cohort_row is None:
            exclusion_records.append({"hn": hn, "reason": reason, "record_count": len(group)})
            continue

        history = group[group["vstdate"] <= cohort_row["index_date"]].copy()
        rows.append(make_feature_row(history, cohort_row))

    return pd.DataFrame(rows), pd.DataFrame(exclusion_records)


def describe_feature(column: str) -> tuple[str, str]:
    if column in TARGET_AND_ID_COLUMNS:
        return "target_or_identifier", "Identifier, index metadata, or target."
    if column in {"history_visit_count", "history_days_observed"}:
        return "history", "Patient history size before or at index date."
    if column in {"index_year", "index_month"}:
        return "date", "Calendar feature from index date."
    if column.endswith("_latest"):
        return "latest", "Latest observed value before or at index date."
    if column.endswith("_mean"):
        return "temporal_summary", "Mean of historical values before or at index date."
    if column.endswith("_min"):
        return "temporal_summary", "Minimum historical value before or at index date."
    if column.endswith("_max"):
        return "temporal_summary", "Maximum historical value before or at index date."
    if column.endswith("_std"):
        return "temporal_summary", "Standard deviation of historical values before or at index date."
    if column.endswith("_count"):
        return "temporal_summary", "Number of non-missing historical values before or at index date."
    if column.endswith("_missing_rate"):
        return "missingness", "Fraction of missing historical values before or at index date."
    return "other", "Engineered patient-level feature."


def build_feature_list(feature_table: pd.DataFrame) -> pd.DataFrame:
    records = []
    for column in feature_table.columns:
        feature_type, description = describe_feature(column)
        records.append(
            {
                "column": column,
                "feature_type": feature_type,
                "is_model_feature": column not in TARGET_AND_ID_COLUMNS,
                "missing_count": int(feature_table[column].isna().sum()),
                "missing_percent": round(float(feature_table[column].isna().mean() * 100), 2),
                "description": description,
            }
        )
    return pd.DataFrame(records)


def write_outputs(
    feature_table: pd.DataFrame,
    exclusions: pd.DataFrame,
    source_path: Path,
    source_columns: list[str],
    config: Config,
) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)

    feature_list = build_feature_list(feature_table)
    feature_log = pd.DataFrame(
        [
            {
                "step": "load_source_data",
                "detail": f"Loaded {source_path}",
                "row_count": None,
            },
            {
                "step": "build_patient_level_feature_table",
                "detail": "Aggregated history at or before index_date only.",
                "row_count": len(feature_table),
            },
            {
                "step": "exclude_leakage_columns",
                "detail": ", ".join([col for col in LEAKAGE_COLUMNS if col in feature_table.columns]) or "none present",
                "row_count": None,
            },
        ]
    )

    paths = {
        "feature_table": config.output_path,
        "feature_list": config.output_dir / "feature_list.csv",
        "feature_generation_log": config.output_dir / "feature_generation_log.csv",
        "feature_engineering_report_json": config.output_dir / "feature_engineering_report.json",
        "feature_engineering_report_md": config.output_dir / "feature_engineering_report.md",
        "exclusions": config.output_dir / "feature_engineering_exclusions.csv",
    }

    feature_table.to_csv(paths["feature_table"], index=False, encoding="utf-8-sig")
    feature_list.to_csv(paths["feature_list"], index=False, encoding="utf-8-sig")
    feature_log.to_csv(paths["feature_generation_log"], index=False, encoding="utf-8-sig")
    exclusions.to_csv(paths["exclusions"], index=False, encoding="utf-8-sig")

    positives = int(feature_table["stroke_3m"].sum()) if "stroke_3m" in feature_table.columns else 0
    payload: dict[str, object] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": str(source_path),
        "feature_table_path": str(config.output_path),
        "horizon_days": config.horizon_days,
        "patient_rows": int(len(feature_table)),
        "positive_patients": positives,
        "negative_patients": int((feature_table["stroke_3m"] == 0).sum()) if "stroke_3m" in feature_table.columns else 0,
        "prevalence_percent": round(float(feature_table["stroke_3m"].mean() * 100), 2)
        if "stroke_3m" in feature_table.columns and len(feature_table)
        else None,
        "model_feature_count": int(feature_list["is_model_feature"].sum()),
        "excluded_patient_count": int(len(exclusions)),
        "leakage_columns_excluded": [col for col in LEAKAGE_COLUMNS if col in source_columns],
        "outputs": {key: str(path) for key, path in paths.items()},
        "checks": {
            "features_use_history_at_or_before_index_date": True,
            "diagnosis_text_columns_used_as_features": False,
            "target": "stroke_3m",
            "unit_of_analysis": "patient",
        },
    }

    paths["feature_engineering_report_json"].write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Feature Engineering Report",
        "",
        f"- Run at: {payload['run_at']}",
        f"- Source: `{payload['source_path']}`",
        f"- Feature table: `{payload['feature_table_path']}`",
        f"- Horizon days: {payload['horizon_days']}",
        f"- Patient rows: {payload['patient_rows']:,}",
        f"- Positive patients: {payload['positive_patients']:,}",
        f"- Negative patients: {payload['negative_patients']:,}",
        f"- Prevalence: {payload['prevalence_percent']}%",
        f"- Model features: {payload['model_feature_count']:,}",
        f"- Excluded patients: {payload['excluded_patient_count']:,}",
        "",
        "## Checks",
        "",
        "- Features use only history at or before index_date.",
        "- Diagnosis/text leakage columns are not model features.",
        "- Target is patient-level `stroke_3m`.",
        "",
        "## Outputs",
        "",
    ]
    for key, path in paths.items():
        lines.append(f"- {key}: `{path}`")
    paths["feature_engineering_report_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def run(config: Config) -> dict[str, object]:
    source_df, source_path = load_source_data(config)
    feature_table, exclusions = build_feature_table(source_df, config)
    return write_outputs(feature_table, exclusions, source_path, list(source_df.columns), config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build patient-level stroke prediction features.")
    parser.add_argument("--input", default=str(Config.input_path), help="Cleaned input CSV path.")
    parser.add_argument("--fallback-input", default=str(Config.fallback_input_path), help="Raw Excel fallback path.")
    parser.add_argument("--output", default=str(Config.output_path), help="Feature table output CSV path.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Feature engineering report directory.")
    parser.add_argument("--horizon-days", type=int, default=Config.horizon_days, help="Prediction horizon in days.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        input_path=Path(args.input),
        fallback_input_path=Path(args.fallback_input),
        output_path=Path(args.output),
        output_dir=Path(args.output_dir),
        horizon_days=args.horizon_days,
    )
    payload = run(config)
    print("Feature engineering completed")
    print(f"Feature table: {payload['feature_table_path']}")
    print(f"Patient rows: {payload['patient_rows']:,}")
    print(f"Positive patients: {payload['positive_patients']:,}")
    print(f"Model features: {payload['model_feature_count']:,}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
