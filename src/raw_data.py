from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class Config:
    input_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    data_dictionary_path: Path = Path("DATASET.md")
    output_dir: Path = Path("output/raw_data_output")


REQUIRED_COLUMN_GROUPS: dict[str, list[str]] = {
    "patient_id": ["hn"],
    "timeline": ["vstdate"],
    "target": ["PrincipleDiagnosis"],
    "demographic": ["sex", "age", "height", "bw", "bmi"],
    "vitals": ["bps", "bpd"],
    "labs": [
        "HDL",
        "LDL",
        "Triglyceride",
        "Cholesterol",
        "FBS",
        "eGFR",
        "Creatinine",
        "TC:HDL_ratio",
    ],
    "behavior_flags": ["smoke", "drinking"],
    "comorbidity_flags": ["AF", "heart_disease", "hypertension", "diabetes"],
    "medication_flags": ["Statin", "Gemfibrozil", "Antihypertensive_flag"],
}


def load_raw_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")
    return pd.read_excel(path)


def infer_column_role(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "unknown_all_missing"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    if pd.api.types.is_numeric_dtype(series):
        unique_values = set(non_null.unique().tolist())
        if unique_values.issubset({0, 1}) or unique_values.issubset({0.0, 1.0}):
            return "flag"
        return "numeric"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed_dates = pd.to_datetime(non_null.head(100), errors="coerce")
    if parsed_dates.notna().mean() >= 0.9:
        return "date_like_text"

    unique_count = non_null.nunique(dropna=True)
    if unique_count <= 20:
        return "categorical_text"
    return "text"


def build_schema_summary(df: pd.DataFrame) -> pd.DataFrame:
    row_count = len(df)
    records: list[dict[str, object]] = []
    for column in df.columns:
        series = df[column]
        records.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "inferred_role": infer_column_role(series),
                "row_count": row_count,
                "non_null_count": int(series.notna().sum()),
                "missing_count": int(series.isna().sum()),
                "missing_percent": round(float(series.isna().mean() * 100), 2),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": "; ".join(map(str, series.dropna().head(3).tolist())),
            }
        )
    return pd.DataFrame(records)


def build_missing_summary(schema_summary: pd.DataFrame) -> pd.DataFrame:
    columns = ["column", "missing_count", "missing_percent", "non_null_count", "row_count", "inferred_role"]
    return (
        schema_summary[columns]
        .sort_values(["missing_count", "missing_percent", "column"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def build_column_availability(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    available_columns = set(df.columns)
    for group, columns in REQUIRED_COLUMN_GROUPS.items():
        for column in columns:
            records.append(
                {
                    "group": group,
                    "column": column,
                    "available": column in available_columns,
                    "note": "present" if column in available_columns else "missing",
                }
            )
    return pd.DataFrame(records)


def write_tables(
    df: pd.DataFrame,
    schema_summary: pd.DataFrame,
    missing_summary: pd.DataFrame,
    availability: pd.DataFrame,
    config: Config,
) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "schema_summary": config.output_dir / "raw_schema_summary.csv",
        "missing_summary": config.output_dir / "raw_missing_summary.csv",
        "column_availability": config.output_dir / "column_availability_checklist.csv",
        "column_list": config.output_dir / "raw_column_list.csv",
    }

    schema_summary.to_csv(output_paths["schema_summary"], index=False, encoding="utf-8-sig")
    missing_summary.to_csv(output_paths["missing_summary"], index=False, encoding="utf-8-sig")
    availability.to_csv(output_paths["column_availability"], index=False, encoding="utf-8-sig")
    pd.DataFrame({"column": df.columns}).to_csv(output_paths["column_list"], index=False, encoding="utf-8-sig")
    return output_paths


def build_report_payload(
    df: pd.DataFrame,
    availability: pd.DataFrame,
    config: Config,
    output_paths: dict[str, Path],
) -> dict[str, object]:
    missing_required = availability.loc[~availability["available"], "column"].tolist()
    return {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_data_path": str(config.input_path),
        "data_dictionary_path": str(config.data_dictionary_path),
        "data_dictionary_exists": config.data_dictionary_path.exists(),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_required_columns": missing_required,
        "outputs": {key: str(path) for key, path in output_paths.items()},
        "checks": {
            "raw_file_was_not_modified": True,
            "has_hn": "hn" in df.columns,
            "has_vstdate": "vstdate" in df.columns,
            "has_principle_diagnosis": "PrincipleDiagnosis" in df.columns,
            "has_tc_hdl_ratio": "TC:HDL_ratio" in df.columns,
        },
    }


def write_reports(payload: dict[str, object], config: Config) -> tuple[Path, Path]:
    json_path = config.output_dir / "raw_data_report.json"
    markdown_path = config.output_dir / "raw_data_report.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    missing_required = payload["missing_required_columns"]
    missing_required_text = ", ".join(missing_required) if missing_required else "none"
    lines = [
        "# Raw Data Report",
        "",
        f"- Run at: {payload['run_at']}",
        f"- Raw data: `{payload['raw_data_path']}`",
        f"- Data dictionary exists: {payload['data_dictionary_exists']}",
        f"- Rows: {payload['row_count']:,}",
        f"- Columns: {payload['column_count']:,}",
        f"- Missing required columns: {missing_required_text}",
        "",
        "## Outputs",
        "",
    ]
    outputs = payload["outputs"]
    for name, path in outputs.items():
        lines.append(f"- {name}: `{path}`")
    lines.extend(
        [
            "- report_json: `output/raw_data_output/raw_data_report.json`",
            "",
            "## Checks",
            "",
        ]
    )
    checks = payload["checks"]
    for name, value in checks.items():
        lines.append(f"- {name}: {value}")

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def run(config: Config) -> dict[str, object]:
    df = load_raw_excel(config.input_path)
    schema_summary = build_schema_summary(df)
    missing_summary = build_missing_summary(schema_summary)
    availability = build_column_availability(df)
    output_paths = write_tables(df, schema_summary, missing_summary, availability, config)
    payload = build_report_payload(df, availability, config, output_paths)
    json_path, markdown_path = write_reports(payload, config)
    payload["outputs"]["report_json"] = str(json_path)
    payload["outputs"]["report_markdown"] = str(markdown_path)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect raw stroke data without modifying the source file.")
    parser.add_argument("--input", default=str(Config.input_path), help="Path to the raw Excel file.")
    parser.add_argument("--data-dictionary", default=str(Config.data_dictionary_path), help="Path to DATASET.md.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Directory for raw data reports.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        input_path=Path(args.input),
        data_dictionary_path=Path(args.data_dictionary),
        output_dir=Path(args.output_dir),
    )
    payload = run(config)
    print("Raw data inspection completed")
    print(f"Rows: {payload['row_count']:,}")
    print(f"Columns: {payload['column_count']:,}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
