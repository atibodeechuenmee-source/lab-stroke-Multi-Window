"""Stage 03 data cleaning for pre-reference clinical records.

งานหลัก:
1) มาตรฐานชื่อคอลัมน์และชนิดข้อมูล
2) de-identification แบบไม่กระทบคอลัมน์ที่จำเป็นต่อ modeling
3) จัดการ duplicate, diagnosis normalization, binary/range validation
4) เก็บ cleaning log เพื่อ trace ได้ว่าแก้อะไรไปบ้าง

ข้อกำกับ:
- ต้องรักษา invariant จาก Stage 02: ห้ามมี post-reference data
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DataCleaningConfig:
    input_path: Path = Path("output/target_cohort_output/pre_reference_records_with_windows.csv")
    output_dir: Path = Path("output/data_cleaning_output")
    patient_id_col: str = "hn"
    visit_date_col: str = "vstdate"
    reference_date_col: str = "reference_date"
    principal_dx_col: str = "PrincipleDiagnosis"
    comorbidity_dx_col: str = "ComorbidityDiagnosis"
    drop_direct_identifiers: bool = True


COLUMN_RENAME_MAP = {
    "hn": "patient_id",
    "vstdate": "visit_date",
    "PrincipleDiagnosis": "principal_diagnosis",
    "ComorbidityDiagnosis": "comorbidity_diagnosis",
    "ยาที่ได้รับ": "medication_text",
    "HDL": "hdl",
    "LDL": "ldl",
    "Triglyceride": "triglyceride",
    "Cholesterol": "cholesterol",
    "AF": "atrial_fibrillation",
    "FBS": "fbs",
    "eGFR": "egfr",
    "Creatinine": "creatinine",
    "Statin": "statin",
    "Gemfibrozil": "gemfibrozil",
    "TC:HDL_ratio": "tc_hdl_ratio",
    "Antihypertensive_flag": "antihypertensive_flag",
}

DATE_COLUMNS = ["visit_date", "reference_date", "first_stroke_date", "last_visit_date", "first_visit_date"]

NUMERIC_COLUMNS = [
    "age",
    "height",
    "bw",
    "bmi",
    "bps",
    "bpd",
    "hdl",
    "ldl",
    "triglyceride",
    "cholesterol",
    "fbs",
    "egfr",
    "creatinine",
    "tc_hdl_ratio",
    "days_before_reference",
    "months_before_reference",
]

BINARY_COLUMNS = [
    "smoke",
    "drinking",
    "atrial_fibrillation",
    "heart_disease",
    "hypertension",
    "diabetes",
    "statin",
    "gemfibrozil",
    "antihypertensive_flag",
    "stroke",
]

PLAUSIBLE_RANGES = {
    "age": (0, 120),
    "height": (30, 250),
    "bw": (1, 300),
    "bmi": (5, 80),
    "bps": (40, 260),
    "bpd": (20, 160),
    "hdl": (1, 200),
    "ldl": (1, 400),
    "triglyceride": (1, 2000),
    "cholesterol": (20, 600),
    "fbs": (20, 600),
    "egfr": (1, 200),
    "creatinine": (0.1, 30),
    "tc_hdl_ratio": (0.1, 20),
    "days_before_reference": (0, 36500),
    "months_before_reference": (0, 1200),
}

DIRECT_IDENTIFIER_COLUMNS = ["ตำบล"]
ICD_TOKEN_PATTERN = re.compile(r"([A-TV-Z][0-9]{2}(?:\.[0-9A-Z]+)?)", re.IGNORECASE)


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


def standardize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """เปลี่ยนชื่อคอลัมน์ให้เป็นมาตรฐานเดียวทั้ง pipeline."""
    rename_map = {old: new for old, new in COLUMN_RENAME_MAP.items() if old in df.columns}
    cleaned = df.rename(columns=rename_map).copy()
    report = pd.DataFrame(
        [{"original_column": old, "standardized_column": new} for old, new in rename_map.items()]
    )
    return cleaned, report


def deidentify(df: pd.DataFrame, drop_direct_identifiers: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ลบ direct/quasi identifiers ที่ไม่จำเป็นต่อการพยากรณ์."""
    if not drop_direct_identifiers:
        return df.copy(), pd.DataFrame(columns=["column", "action", "reason"])
    dropped = [column for column in DIRECT_IDENTIFIER_COLUMNS if column in df.columns]
    cleaned = df.drop(columns=dropped, errors="ignore").copy()
    report = pd.DataFrame(
        [
            {
                "column": column,
                "action": "dropped",
                "reason": "Direct or quasi identifier not needed for modeling",
            }
            for column in dropped
        ]
    )
    return cleaned, report


def standardize_dates_and_types(df: pd.DataFrame) -> pd.DataFrame:
    """แปลง date/numeric/binary columns ให้พร้อมใช้งานขั้นต่อไป."""
    cleaned = df.copy()
    for column in DATE_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    for column in BINARY_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def normalize_diagnosis_value(value: object) -> str | float:
    """ดึง ICD tokens ออกจากข้อความ diagnosis ให้เป็นรูปแบบสม่ำเสมอ."""
    if pd.isna(value):
        return np.nan
    tokens = ICD_TOKEN_PATTERN.findall(str(value).upper())
    if not tokens:
        return np.nan
    return ";".join(dict.fromkeys(tokens))


def normalize_diagnoses(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = df.copy()
    rows = []
    for column in ["principal_diagnosis", "comorbidity_diagnosis"]:
        if column not in cleaned.columns:
            continue
        normalized_col = f"{column}_normalized"
        cleaned[normalized_col] = cleaned[column].apply(normalize_diagnosis_value)
        rows.append(
            {
                "source_column": column,
                "normalized_column": normalized_col,
                "non_null_before": int(cleaned[column].notna().sum()),
                "non_null_after": int(cleaned[normalized_col].notna().sum()),
            }
        )
    return cleaned, pd.DataFrame(rows)


def drop_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ลบแถวที่ซ้ำแบบ 1:1 เพื่อกันข้อมูลซ้ำเชิงเทคนิค."""
    before = len(df)
    cleaned = df.drop_duplicates().copy()
    report = pd.DataFrame(
        [
            {
                "rule": "drop_exact_duplicates",
                "rows_before": before,
                "rows_after": len(cleaned),
                "rows_changed": before - len(cleaned),
            }
        ]
    )
    return cleaned, report


def apply_binary_encoding(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """คงเฉพาะ binary ที่ถูกต้อง (0/1) ค่าอื่นตั้งเป็น missing."""
    cleaned = df.copy()
    rows = []
    for column in BINARY_COLUMNS:
        if column not in cleaned.columns:
            continue
        before_invalid = int((cleaned[column].notna() & ~cleaned[column].isin([0, 1])).sum())
        cleaned.loc[cleaned[column].notna() & ~cleaned[column].isin([0, 1]), column] = np.nan
        rows.append(
            {
                "column": column,
                "encoding": "{0,1}",
                "invalid_values_set_missing": before_invalid,
                "non_null_after": int(cleaned[column].notna().sum()),
            }
        )
    return cleaned, pd.DataFrame(rows)


def apply_range_checks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ตรวจ plausible ranges และตั้งค่านอกช่วงเป็น missing พร้อม log."""
    cleaned = df.copy()
    summary_rows = []
    log_rows = []
    for column, (low, high) in PLAUSIBLE_RANGES.items():
        if column not in cleaned.columns:
            continue
        values = pd.to_numeric(cleaned[column], errors="coerce")
        invalid_mask = values.notna() & ~values.between(low, high)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            examples = cleaned.loc[invalid_mask, [column]].head(10)
            for idx, row in examples.iterrows():
                log_rows.append(
                    {
                        "row_index": int(idx),
                        "column": column,
                        "original_value": row[column],
                        "action": "set_missing",
                        "reason": f"outside plausible range [{low}, {high}]",
                    }
                )
            cleaned.loc[invalid_mask, column] = np.nan
        summary_rows.append(
            {
                "column": column,
                "expected_min": low,
                "expected_max": high,
                "invalid_values_set_missing": invalid_count,
                "missing_after": int(cleaned[column].isna().sum()),
                "min_after": float(cleaned[column].min()) if cleaned[column].notna().any() else None,
                "max_after": float(cleaned[column].max()) if cleaned[column].notna().any() else None,
            }
        )
    return cleaned, pd.DataFrame(summary_rows), pd.DataFrame(log_rows)


def build_missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.columns:
        rows.append(
            {
                "column": column,
                "missing_count": int(df[column].isna().sum()),
                "missing_percent": float(df[column].isna().mean()) if len(df) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["missing_percent", "missing_count"], ascending=False)


def check_no_post_reference_records(df: pd.DataFrame) -> bool | None:
    """ยืนยันซ้ำว่า cleaned data ยังไม่หลุด post-reference."""
    if "visit_date" not in df.columns or "reference_date" not in df.columns:
        return None
    valid = df[["visit_date", "reference_date"]].dropna()
    if valid.empty:
        return None
    return bool((valid["visit_date"] <= valid["reference_date"]).all())


def build_report_markdown(report: dict[str, object], config: DataCleaningConfig) -> str:
    return f"""# Data Cleaning Report

## Summary

- Input: `{config.input_path}`
- Rows before cleaning: {report["rows_before"]:,}
- Rows after cleaning: {report["rows_after"]:,}
- Columns after cleaning: {report["columns_after"]:,}
- Exact duplicate rows removed: {report["duplicate_rows_removed"]:,}
- Direct identifier columns dropped: {report["direct_identifier_columns_dropped"]}
- Range-invalid values set missing: {report["range_invalid_values_set_missing"]:,}
- Binary-invalid values set missing: {report["binary_invalid_values_set_missing"]:,}
- No post-reference records: `{report["no_post_reference_records"]}`

## Outputs

- `cleaned_pre_reference_records.csv`
- `cleaning_report.json`
- `cleaning_report.md`
- `cleaning_log.csv`
- `missing_summary_after_cleaning.csv`
- `range_summary_after_cleaning.csv`
- `binary_flag_encoding_map.csv`
- `diagnosis_normalization_report.csv`
- `column_standardization_report.csv`
- `deidentification_report.csv`

## Notes

Stage 03 keeps patient id because it is required for patient-level feature engineering, but drops direct/quasi identifiers that are not needed for modeling. It preserves the Stage 02 no-post-reference-data invariant.
"""


def run_data_cleaning(config: DataCleaningConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 03."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    raw = load_records(config.input_path)
    rows_before = len(raw)

    cleaned, column_report = standardize_columns(raw)
    cleaned, deid_report = deidentify(cleaned, config.drop_direct_identifiers)
    cleaned = standardize_dates_and_types(cleaned)
    cleaned, duplicate_report = drop_exact_duplicates(cleaned)
    cleaned, diagnosis_report = normalize_diagnoses(cleaned)
    cleaned, binary_report = apply_binary_encoding(cleaned)
    cleaned, range_report, range_log = apply_range_checks(cleaned)

    missing_summary = build_missing_summary(cleaned)
    no_post_reference = check_no_post_reference_records(cleaned)
    duplicate_rows_removed = int(duplicate_report["rows_changed"].sum()) if not duplicate_report.empty else 0
    binary_invalid = int(binary_report["invalid_values_set_missing"].sum()) if not binary_report.empty else 0
    range_invalid = int(range_report["invalid_values_set_missing"].sum()) if not range_report.empty else 0

    # รวม log จากหลายแหล่งให้ตรวจย้อนหลังได้ง่ายในไฟล์เดียว
    log_parts = []
    if not range_log.empty:
        log_parts.append(range_log)
    if not duplicate_report.empty:
        log_parts.append(duplicate_report.assign(row_index="", column="", original_value="", action="drop_rows"))
    cleaning_log = pd.concat(log_parts, ignore_index=True, sort=False) if log_parts else pd.DataFrame()

    report = {
        "input_path": str(config.input_path),
        "output_dir": str(config.output_dir),
        "rows_before": int(rows_before),
        "rows_after": int(len(cleaned)),
        "columns_after": int(cleaned.shape[1]),
        "duplicate_rows_removed": duplicate_rows_removed,
        "direct_identifier_columns_dropped": deid_report["column"].tolist() if not deid_report.empty else [],
        "range_invalid_values_set_missing": range_invalid,
        "binary_invalid_values_set_missing": binary_invalid,
        "no_post_reference_records": no_post_reference,
    }

    write_csv(cleaned, config.output_dir / "cleaned_pre_reference_records.csv")
    write_csv(missing_summary, config.output_dir / "missing_summary_after_cleaning.csv")
    write_csv(range_report, config.output_dir / "range_summary_after_cleaning.csv")
    write_csv(binary_report, config.output_dir / "binary_flag_encoding_map.csv")
    write_csv(diagnosis_report, config.output_dir / "diagnosis_normalization_report.csv")
    write_csv(column_report, config.output_dir / "column_standardization_report.csv")
    write_csv(deid_report, config.output_dir / "deidentification_report.csv")
    write_csv(cleaning_log, config.output_dir / "cleaning_log.csv")
    write_json(report, config.output_dir / "cleaning_report.json")
    (config.output_dir / "cleaning_report.md").write_text(build_report_markdown(report, config), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 03 data cleaning.")
    parser.add_argument("--input-path", default=str(DataCleaningConfig.input_path), help="Stage 02 pre-reference CSV.")
    parser.add_argument("--output-dir", default=str(DataCleaningConfig.output_dir), help="Cleaning output directory.")
    parser.add_argument("--keep-direct-identifiers", action="store_true", help="Do not drop direct identifier columns.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = DataCleaningConfig(
        input_path=Path(args.input_path),
        output_dir=Path(args.output_dir),
        drop_direct_identifiers=not args.keep_direct_identifiers,
    )
    report = run_data_cleaning(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
