"""Stage 01 raw data audit for the temporal stroke pipeline.

This module implements docs/pipeline/01-raw-data.md. It only reads the
raw file and writes audit outputs; it never edits or overwrites raw data.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


STROKE_PATTERN = re.compile(r"\bI6[0-8](?:\.\d+)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class RawDataConfig:
    raw_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/raw_data_output")
    patient_id_col: str = "hn"
    visit_date_col: str = "vstdate"
    principal_dx_col: str = "PrincipleDiagnosis"
    comorbidity_dx_col: str = "ComorbidityDiagnosis"


EXPECTED_COLUMNS = {
    "patient_identifier": ["hn", "HN", "patient_id"],
    "visit_date": ["vstdate", "visit_date", "service_date"],
    "principal_diagnosis": ["PrincipleDiagnosis", "PrincipalDiagnosis", "principal_diagnosis"],
    "comorbidity_diagnosis": ["ComorbidityDiagnosis", "comorbidity_diagnosis"],
    "sex": ["sex"],
    "age": ["age"],
    "height": ["height"],
    "body_weight": ["bw", "weight"],
    "bmi": ["bmi", "BMI"],
    "smoking": ["smoke", "smoking"],
    "drinking": ["drinking", "alcohol"],
    "systolic_bp": ["bps", "BPS"],
    "diastolic_bp": ["bpd", "BPD"],
    "hdl": ["HDL", "hdl"],
    "ldl": ["LDL", "ldl"],
    "triglyceride": ["Triglyceride", "triglyceride"],
    "total_cholesterol": ["Cholesterol", "cholesterol", "total_cholesterol"],
    "atrial_fibrillation": ["AF", "af"],
    "fasting_blood_sugar": ["FBS", "fbs"],
    "egfr": ["eGFR", "egfr"],
    "creatinine": ["Creatinine", "creatinine"],
    "medication": ["ยาที่ได้รับ", "medication", "drug"],
    "heart_disease": ["heart_disease"],
    "hypertension": ["hypertension"],
    "diabetes": ["diabetes"],
    "statin": ["Statin", "statin"],
    "gemfibrozil": ["Gemfibrozil", "gemfibrozil"],
    "tc_hdl_ratio": ["TC:HDL_ratio", "TC_HDL_ratio", "tc_hdl_ratio"],
    "antihypertensive_flag": ["Antihypertensive_flag", "antihypertensive_flag"],
}

RANGE_CHECKS = {
    "age": (0, 120),
    "height": (30, 250),
    "bw": (1, 300),
    "bmi": (5, 80),
    "bps": (40, 260),
    "bpd": (20, 160),
    "HDL": (1, 200),
    "LDL": (1, 400),
    "Triglyceride": (1, 2000),
    "Cholesterol": (20, 600),
    "FBS": (20, 600),
    "eGFR": (1, 200),
    "Creatinine": (0.1, 30),
    "TC:HDL_ratio": (0.1, 20),
}


def load_raw_data(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported raw data file: {path}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def first_existing(columns: set[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def build_column_list(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"ordinal": range(1, len(df.columns) + 1), "column": df.columns})


def build_schema_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_rows = len(df)
    for column in df.columns:
        non_null = df[column].dropna()
        rows.append(
            {
                "column": column,
                "dtype": str(df[column].dtype),
                "non_null_count": int(non_null.shape[0]),
                "missing_count": int(df[column].isna().sum()),
                "missing_percent": float(df[column].isna().mean()) if total_rows else 0.0,
                "unique_count": int(non_null.nunique(dropna=True)),
                "example_values": "; ".join(non_null.astype(str).head(5).tolist()),
            }
        )
    return pd.DataFrame(rows)


def build_missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = build_schema_summary(df)[["column", "missing_count", "missing_percent"]].copy()
    return summary.sort_values(["missing_percent", "missing_count"], ascending=False)


def build_column_availability(df: pd.DataFrame) -> pd.DataFrame:
    columns = set(map(str, df.columns))
    rows = []
    for required_field, candidates in EXPECTED_COLUMNS.items():
        matched = first_existing(columns, candidates)
        rows.append(
            {
                "required_field": required_field,
                "status": "available" if matched else "missing",
                "matched_column": matched or "",
                "candidate_columns": ", ".join(candidates),
            }
        )
    return pd.DataFrame(rows)


def build_visit_coverage(df: pd.DataFrame, config: RawDataConfig) -> pd.DataFrame:
    if config.patient_id_col not in df.columns or config.visit_date_col not in df.columns:
        return pd.DataFrame()
    visits = df[[config.patient_id_col, config.visit_date_col]].copy()
    visits[config.visit_date_col] = pd.to_datetime(visits[config.visit_date_col], errors="coerce")
    visits = visits.dropna(subset=[config.patient_id_col, config.visit_date_col])
    grouped = visits.groupby(config.patient_id_col)[config.visit_date_col]
    coverage = grouped.agg(["count", "min", "max"]).reset_index()
    coverage = coverage.rename(
        columns={
            "count": "record_count",
            "min": "first_visit_date",
            "max": "last_visit_date",
        }
    )
    coverage["followup_days"] = (coverage["last_visit_date"] - coverage["first_visit_date"]).dt.days
    return coverage


def build_range_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column, (low, high) in RANGE_CHECKS.items():
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce")
        rows.append(
            {
                "column": column,
                "non_null_count": int(values.notna().sum()),
                "min": float(values.min()) if values.notna().any() else None,
                "max": float(values.max()) if values.notna().any() else None,
                "below_expected_count": int((values < low).sum()),
                "above_expected_count": int((values > high).sum()),
                "expected_min": low,
                "expected_max": high,
            }
        )
    return pd.DataFrame(rows)


def _contains_stroke_code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.contains(STROKE_PATTERN, na=False)


def build_icd_availability(df: pd.DataFrame, config: RawDataConfig) -> pd.DataFrame:
    rows = []
    for diagnosis_role, column in {
        "principal": config.principal_dx_col,
        "comorbidity": config.comorbidity_dx_col,
    }.items():
        if column not in df.columns:
            rows.append(
                {
                    "diagnosis_role": diagnosis_role,
                    "column": column,
                    "status": "missing",
                    "non_null_count": 0,
                    "stroke_code_record_count": 0,
                    "example_stroke_codes": "",
                }
            )
            continue
        mask = _contains_stroke_code(df[column])
        rows.append(
            {
                "diagnosis_role": diagnosis_role,
                "column": column,
                "status": "available",
                "non_null_count": int(df[column].notna().sum()),
                "stroke_code_record_count": int(mask.sum()),
                "example_stroke_codes": "; ".join(df.loc[mask, column].dropna().astype(str).head(10).tolist()),
            }
        )
    return pd.DataFrame(rows)


def build_report_markdown(
    df: pd.DataFrame,
    config: RawDataConfig,
    column_availability: pd.DataFrame,
    visit_coverage: pd.DataFrame,
    icd_availability: pd.DataFrame,
) -> str:
    available_required = int((column_availability["status"] == "available").sum())
    missing_required = int((column_availability["status"] == "missing").sum())
    patient_count = int(df[config.patient_id_col].nunique()) if config.patient_id_col in df.columns else 0
    date_min = ""
    date_max = ""
    if config.visit_date_col in df.columns:
        dates = pd.to_datetime(df[config.visit_date_col], errors="coerce")
        date_min = str(dates.min().date()) if dates.notna().any() else ""
        date_max = str(dates.max().date()) if dates.notna().any() else ""

    stroke_records = int(icd_availability["stroke_code_record_count"].sum()) if not icd_availability.empty else 0
    coverage_text = "ไม่สามารถคำนวณได้ เพราะไม่มี patient/date column"
    if not visit_coverage.empty:
        coverage_text = (
            f"records per patient median = {visit_coverage['record_count'].median():.1f}, "
            f"max = {int(visit_coverage['record_count'].max())}"
        )

    return f"""# Raw Data Audit Report

## Summary

- Raw file: `{config.raw_path}`
- Rows: {len(df):,}
- Columns: {df.shape[1]:,}
- Patients: {patient_count:,}
- Visit date range: {date_min} to {date_max}
- Required fields available: {available_required}
- Required fields missing: {missing_required}
- Stroke ICD `I60-I68` record hits: {stroke_records:,}
- Visit coverage: {coverage_text}

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

- Patient identifier found: `{config.patient_id_col in df.columns}`
- Visit date found: `{config.visit_date_col in df.columns}`
- Principal diagnosis found: `{config.principal_dx_col in df.columns}`
- Comorbidity diagnosis found: `{config.comorbidity_dx_col in df.columns}`
- Raw data was read-only: `true`

## Notes

Stage 01 does not clean, drop, overwrite, or mutate the raw source file. It only produces audit artifacts for the later cleaning and cohort-construction stages.
"""


def run_raw_data_audit(config: RawDataConfig) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_raw_data(config.raw_path)

    column_list = build_column_list(df)
    schema_summary = build_schema_summary(df)
    missing_summary = build_missing_summary(df)
    column_availability = build_column_availability(df)
    visit_coverage = build_visit_coverage(df, config)
    range_summary = build_range_summary(df)
    icd_availability = build_icd_availability(df, config)

    write_csv(column_list, config.output_dir / "raw_column_list.csv")
    write_csv(schema_summary, config.output_dir / "raw_schema_summary.csv")
    write_csv(missing_summary, config.output_dir / "raw_missing_summary.csv")
    write_csv(column_availability, config.output_dir / "column_availability_checklist.csv")
    write_csv(visit_coverage, config.output_dir / "visit_coverage_summary.csv")
    write_csv(range_summary, config.output_dir / "raw_range_summary.csv")
    write_csv(icd_availability, config.output_dir / "icd10_availability_report.csv")

    report = {
        "raw_path": str(config.raw_path),
        "output_dir": str(config.output_dir),
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "patients": int(df[config.patient_id_col].nunique()) if config.patient_id_col in df.columns else None,
        "required_fields_available": int((column_availability["status"] == "available").sum()),
        "required_fields_missing": int((column_availability["status"] == "missing").sum()),
        "stroke_icd_record_hits": int(icd_availability["stroke_code_record_count"].sum()),
    }
    write_json(report, config.output_dir / "raw_data_report.json")
    (config.output_dir / "raw_data_report.md").write_text(
        build_report_markdown(df, config, column_availability, visit_coverage, icd_availability),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 01 raw EHR data audit.")
    parser.add_argument("--raw-path", default=str(RawDataConfig.raw_path), help="Raw Excel/CSV path.")
    parser.add_argument("--output-dir", default=str(RawDataConfig.output_dir), help="Audit output directory.")
    parser.add_argument("--patient-id-col", default=RawDataConfig.patient_id_col)
    parser.add_argument("--visit-date-col", default=RawDataConfig.visit_date_col)
    parser.add_argument("--principal-dx-col", default=RawDataConfig.principal_dx_col)
    parser.add_argument("--comorbidity-dx-col", default=RawDataConfig.comorbidity_dx_col)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RawDataConfig(
        raw_path=Path(args.raw_path),
        output_dir=Path(args.output_dir),
        patient_id_col=args.patient_id_col,
        visit_date_col=args.visit_date_col,
        principal_dx_col=args.principal_dx_col,
        comorbidity_dx_col=args.comorbidity_dx_col,
    )
    report = run_raw_data_audit(config)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

