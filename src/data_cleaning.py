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
    input_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/data_cleaning_output")
    cleaned_path: Path = Path("data/interim/cleaned_stroke_records.csv")
    missing_indicator_threshold: float = 0.05


DATE_COLUMNS = ["vstdate"]

NUMERIC_COLUMNS = [
    "hn",
    "sex",
    "age",
    "height",
    "bw",
    "bmi",
    "smoke",
    "drinking",
    "bps",
    "bpd",
    "HDL",
    "LDL",
    "Triglyceride",
    "Cholesterol",
    "AF",
    "FBS",
    "eGFR",
    "Creatinine",
    "heart_disease",
    "hypertension",
    "diabetes",
    "Statin",
    "Gemfibrozil",
    "TC:HDL_ratio",
    "Antihypertensive_flag",
]

TEXT_COLUMNS = ["PrincipleDiagnosis", "ComorbidityDiagnosis", "ตำบล", "ยาที่ได้รับ"]

BINARY_FLAG_COLUMNS = [
    "heart_disease",
    "hypertension",
    "diabetes",
    "Statin",
    "Gemfibrozil",
    "Antihypertensive_flag",
]

MISSING_INDICATOR_CANDIDATES = [
    "height",
    "bw",
    "bmi",
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

# Fixed plausibility bounds. These are not learned from the dataset.
CLINICAL_RANGES: dict[str, tuple[float, float]] = {
    "age": (0, 120),
    "height": (80, 230),
    "bw": (20, 300),
    "bmi": (10, 80),
    "bps": (60, 260),
    "bpd": (30, 160),
    "HDL": (1, 200),
    "LDL": (1, 400),
    "Triglyceride": (1, 2000),
    "Cholesterol": (1, 500),
    "FBS": (30, 600),
    "eGFR": (0, 200),
    "Creatinine": (0.1, 20),
    "TC:HDL_ratio": (0.1, 20),
}


def build_stroke_flag(df: pd.DataFrame) -> pd.Series:
    diagnosis = df["PrincipleDiagnosis"].astype("string").str.strip().fillna("")
    return diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def load_raw_data(config: Config) -> pd.DataFrame:
    if not config.input_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {config.input_path}")
    return pd.read_excel(config.input_path)


def coerce_types(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    logs: list[dict[str, object]] = []

    for column in DATE_COLUMNS:
        if column not in cleaned.columns:
            continue
        before_missing = int(cleaned[column].isna().sum())
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
        after_missing = int(cleaned[column].isna().sum())
        logs.append(
            {
                "step": "coerce_date",
                "column": column,
                "values_set_missing": after_missing - before_missing,
            }
        )

    for column in NUMERIC_COLUMNS:
        if column not in cleaned.columns:
            continue
        before_missing = int(cleaned[column].isna().sum())
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
        after_missing = int(cleaned[column].isna().sum())
        logs.append(
            {
                "step": "coerce_numeric",
                "column": column,
                "values_set_missing": after_missing - before_missing,
            }
        )

    for column in TEXT_COLUMNS:
        if column not in cleaned.columns:
            continue
        cleaned[column] = cleaned[column].astype("string").str.strip()
        cleaned.loc[cleaned[column] == "", column] = pd.NA
        logs.append({"step": "strip_text", "column": column, "values_set_missing": None})

    return cleaned, logs


def drop_invalid_required_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    required = ["hn", "vstdate"]
    available = [column for column in required if column in df.columns]
    before = len(df)
    cleaned = df.dropna(subset=available).copy()
    return cleaned, {
        "step": "drop_missing_required_fields",
        "rows_before": before,
        "rows_after": len(cleaned),
        "rows_removed": before - len(cleaned),
        "required_fields": available,
    }


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    logs: list[dict[str, object]] = []
    before = len(df)
    cleaned = df.drop_duplicates().copy()
    logs.append(
        {
            "step": "drop_exact_duplicate_rows",
            "rows_before": before,
            "rows_after": len(cleaned),
            "rows_removed": before - len(cleaned),
        }
    )

    subset = [column for column in ["hn", "vstdate", "PrincipleDiagnosis"] if column in cleaned.columns]
    before = len(cleaned)
    if subset:
        cleaned = cleaned.drop_duplicates(subset=subset, keep="first").copy()
    logs.append(
        {
            "step": "drop_duplicate_patient_visit_diagnosis",
            "rows_before": before,
            "rows_after": len(cleaned),
            "rows_removed": before - len(cleaned),
            "subset": subset,
        }
    )
    return cleaned, logs


def clean_binary_flags(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    logs: list[dict[str, object]] = []
    for column in BINARY_FLAG_COLUMNS:
        if column not in cleaned.columns:
            continue
        invalid_mask = cleaned[column].notna() & ~cleaned[column].isin([0, 1])
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            cleaned.loc[invalid_mask, column] = pd.NA
        logs.append({"step": "validate_binary_flag", "column": column, "values_set_missing": invalid_count})
    return cleaned, logs


def apply_clinical_ranges(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    logs: list[dict[str, object]] = []
    for column, (lower, upper) in CLINICAL_RANGES.items():
        if column not in cleaned.columns:
            continue
        invalid_mask = cleaned[column].notna() & ~cleaned[column].between(lower, upper, inclusive="both")
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            cleaned.loc[invalid_mask, column] = pd.NA
        logs.append(
            {
                "step": "apply_fixed_clinical_range",
                "column": column,
                "lower_bound": lower,
                "upper_bound": upper,
                "values_set_missing": invalid_count,
            }
        )
    return cleaned, logs


def add_missing_indicators(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    logs: list[dict[str, object]] = []
    for column in MISSING_INDICATOR_CANDIDATES:
        if column not in cleaned.columns:
            continue
        missing_rate = float(cleaned[column].isna().mean())
        added = missing_rate >= threshold
        if added:
            cleaned[f"{column}_missing_indicator"] = cleaned[column].isna().astype(int)
        logs.append(
            {
                "step": "add_missing_indicator",
                "column": column,
                "missing_rate": round(missing_rate, 6),
                "indicator_added": added,
            }
        )
    return cleaned, logs


def summarize_missing(df: pd.DataFrame) -> pd.DataFrame:
    row_count = len(df)
    return (
        pd.DataFrame(
            {
                "column": df.columns,
                "non_null_count": df.notna().sum().values,
                "missing_count": df.isna().sum().values,
                "missing_percent": df.isna().mean().mul(100).round(2).values,
                "row_count": row_count,
            }
        )
        .sort_values(["missing_count", "column"], ascending=[False, True])
        .reset_index(drop=True)
    )


def summarize_ranges(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for column, (lower, upper) in CLINICAL_RANGES.items():
        if column not in df.columns:
            continue
        series = df[column]
        records.append(
            {
                "column": column,
                "lower_bound": lower,
                "upper_bound": upper,
                "non_null_count": int(series.notna().sum()),
                "min": series.min(skipna=True),
                "max": series.max(skipna=True),
                "missing_count": int(series.isna().sum()),
                "missing_percent": round(float(series.isna().mean() * 100), 2),
            }
        )
    return pd.DataFrame(records)


def build_report_payload(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    logs: list[dict[str, object]],
    config: Config,
) -> dict[str, object]:
    raw_target = build_stroke_flag(raw_df) if "PrincipleDiagnosis" in raw_df.columns else pd.Series(dtype=int)
    cleaned_target = build_stroke_flag(cleaned_df) if "PrincipleDiagnosis" in cleaned_df.columns else pd.Series(dtype=int)
    indicator_columns = [column for column in cleaned_df.columns if column.endswith("_missing_indicator")]

    return {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_data_path": str(config.input_path),
        "cleaned_data_path": str(config.cleaned_path),
        "raw_rows": int(len(raw_df)),
        "cleaned_rows": int(len(cleaned_df)),
        "rows_removed": int(len(raw_df) - len(cleaned_df)),
        "raw_positive_records": int(raw_target.sum()) if not raw_target.empty else None,
        "cleaned_positive_records": int(cleaned_target.sum()) if not cleaned_target.empty else None,
        "missing_indicator_columns": indicator_columns,
        "rules": {
            "imputation": "not_applied_to_avoid_train_test_leakage",
            "scaling": "not_applied_to_avoid_train_test_leakage",
            "encoding": "not_applied_to_avoid_train_test_leakage",
            "outlier_policy": "fixed_clinical_ranges_set_impossible_values_to_missing",
            "duplicate_policy": "drop_exact_duplicates_then_patient_visit_diagnosis_duplicates",
        },
        "logs": logs,
    }


def write_outputs(
    cleaned_df: pd.DataFrame,
    logs: list[dict[str, object]],
    payload: dict[str, object],
    config: Config,
) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.cleaned_path.parent.mkdir(parents=True, exist_ok=True)

    paths = {
        "cleaned_dataset": config.cleaned_path,
        "cleaning_log": config.output_dir / "cleaning_log.csv",
        "missing_summary_after_cleaning": config.output_dir / "missing_summary_after_cleaning.csv",
        "range_summary_after_cleaning": config.output_dir / "range_summary_after_cleaning.csv",
        "cleaning_report_json": config.output_dir / "cleaning_report.json",
        "cleaning_report_md": config.output_dir / "cleaning_report.md",
    }
    payload["outputs"] = {key: str(path) for key, path in paths.items()}

    cleaned_df.to_csv(paths["cleaned_dataset"], index=False, encoding="utf-8-sig")
    pd.DataFrame(logs).to_csv(paths["cleaning_log"], index=False, encoding="utf-8-sig")
    summarize_missing(cleaned_df).to_csv(paths["missing_summary_after_cleaning"], index=False, encoding="utf-8-sig")
    summarize_ranges(cleaned_df).to_csv(paths["range_summary_after_cleaning"], index=False, encoding="utf-8-sig")
    paths["cleaning_report_json"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Data Cleaning Report",
        "",
        f"- Run at: {payload['run_at']}",
        f"- Raw data: `{payload['raw_data_path']}`",
        f"- Cleaned data: `{payload['cleaned_data_path']}`",
        f"- Raw rows: {payload['raw_rows']:,}",
        f"- Cleaned rows: {payload['cleaned_rows']:,}",
        f"- Rows removed: {payload['rows_removed']:,}",
        f"- Raw positive records: {payload['raw_positive_records']}",
        f"- Cleaned positive records: {payload['cleaned_positive_records']}",
        "",
        "## Rules",
        "",
    ]
    for key, value in payload["rules"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Missing Indicators", ""])
    if payload["missing_indicator_columns"]:
        for column in payload["missing_indicator_columns"]:
            lines.append(f"- `{column}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Outputs", ""])
    for key, path in paths.items():
        lines.append(f"- {key}: `{path}`")

    paths["cleaning_report_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paths


def run(config: Config) -> dict[str, object]:
    raw_df = load_raw_data(config)
    logs: list[dict[str, object]] = []

    cleaned_df, step_logs = coerce_types(raw_df)
    logs.extend(step_logs)

    cleaned_df, required_log = drop_invalid_required_rows(cleaned_df)
    logs.append(required_log)

    cleaned_df, step_logs = drop_duplicates(cleaned_df)
    logs.extend(step_logs)

    cleaned_df, step_logs = clean_binary_flags(cleaned_df)
    logs.extend(step_logs)

    cleaned_df, step_logs = apply_clinical_ranges(cleaned_df)
    logs.extend(step_logs)

    cleaned_df, step_logs = add_missing_indicators(cleaned_df, config.missing_indicator_threshold)
    logs.extend(step_logs)

    payload = build_report_payload(raw_df, cleaned_df, logs, config)
    paths = write_outputs(cleaned_df, logs, payload, config)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean raw stroke records without modifying the raw file.")
    parser.add_argument("--input", default=str(Config.input_path), help="Path to the raw Excel file.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Directory for cleaning reports.")
    parser.add_argument("--cleaned-path", default=str(Config.cleaned_path), help="Path for the cleaned dataset CSV.")
    parser.add_argument(
        "--missing-indicator-threshold",
        type=float,
        default=Config.missing_indicator_threshold,
        help="Add missing indicators for columns with missing rate at or above this fraction.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        cleaned_path=Path(args.cleaned_path),
        missing_indicator_threshold=args.missing_indicator_threshold,
    )
    payload = run(config)
    print("Data cleaning completed")
    print(f"Raw rows: {payload['raw_rows']:,}")
    print(f"Cleaned rows: {payload['cleaned_rows']:,}")
    print(f"Rows removed: {payload['rows_removed']:,}")
    print(f"Cleaned data: {payload['cleaned_data_path']}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
