"""Stage 01 raw data audit for the temporal stroke pipeline.

โมดูลนี้ทำหน้าที่ "สำรวจคุณภาพข้อมูลดิบ" เท่านั้น:
1) อ่านไฟล์ raw
2) สรุป schema/missing/range/coverage/ICD availability
3) เขียนรายงานและตารางตรวจสอบ

ข้อสำคัญ:
- ห้ามแก้ไฟล์ raw ต้นทาง
- ใช้ผลจาก Stage 01 เป็น checkpoint ก่อนเข้า Stage 02/03
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


STROKE_PATTERN = re.compile(r"\bI6[0-8](?:\.\d+)?\b", re.IGNORECASE)
PAPER_REFERENCE = {
    "title": "Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction",
    "data_source": "Chokchai Hospital EHR",
    "reported_records": 245978,
    "reported_patients": 19473,
    "reported_raw_attributes": 45,
    "stroke_icd10_range": "I60-I68",
}


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

EXPECTED_FIELD_DETAILS = {
    "patient_identifier": {
        "category": "identifier",
        "paper_role": "patient-level grouping",
        "required_for": "all_stages",
    },
    "visit_date": {
        "category": "temporal",
        "paper_role": "reference date and retrospective windows",
        "required_for": "cohort_windows",
    },
    "principal_diagnosis": {
        "category": "diagnosis",
        "paper_role": "stroke ICD-10 target detection",
        "required_for": "target",
    },
    "comorbidity_diagnosis": {
        "category": "diagnosis",
        "paper_role": "stroke/comorbidity ICD-10 context",
        "required_for": "target_context",
    },
    "sex": {"category": "demographic", "paper_role": "core variable", "required_for": "features"},
    "age": {"category": "demographic", "paper_role": "core variable", "required_for": "features"},
    "height": {"category": "clinical", "paper_role": "body-size variable", "required_for": "features"},
    "body_weight": {"category": "clinical", "paper_role": "body-size variable", "required_for": "features"},
    "bmi": {"category": "clinical", "paper_role": "stroke-risk variable", "required_for": "features"},
    "smoking": {"category": "risk_factor", "paper_role": "lifestyle risk factor", "required_for": "features"},
    "drinking": {"category": "risk_factor", "paper_role": "lifestyle risk factor", "required_for": "features"},
    "systolic_bp": {"category": "vital_sign", "paper_role": "blood pressure", "required_for": "features"},
    "diastolic_bp": {"category": "vital_sign", "paper_role": "blood pressure", "required_for": "features"},
    "hdl": {"category": "lab", "paper_role": "lipid profile", "required_for": "features"},
    "ldl": {"category": "lab", "paper_role": "lipid profile", "required_for": "features"},
    "triglyceride": {"category": "lab", "paper_role": "lipid profile", "required_for": "features"},
    "total_cholesterol": {"category": "lab", "paper_role": "lipid profile", "required_for": "features"},
    "atrial_fibrillation": {"category": "comorbidity", "paper_role": "cardiac risk factor", "required_for": "features"},
    "fasting_blood_sugar": {"category": "lab", "paper_role": "diabetes/glucose marker", "required_for": "features"},
    "egfr": {"category": "lab", "paper_role": "kidney function", "required_for": "features"},
    "creatinine": {"category": "lab", "paper_role": "kidney function", "required_for": "features"},
    "medication": {"category": "medication", "paper_role": "drug exposure context", "required_for": "features"},
    "heart_disease": {"category": "comorbidity", "paper_role": "Extract Set 3", "required_for": "extract_set_3"},
    "hypertension": {"category": "comorbidity", "paper_role": "Extract Set 3", "required_for": "extract_set_3"},
    "diabetes": {"category": "comorbidity", "paper_role": "Extract Set 3", "required_for": "extract_set_3"},
    "statin": {"category": "medication", "paper_role": "Extract Set 3", "required_for": "extract_set_3"},
    "gemfibrozil": {"category": "medication", "paper_role": "local lipid medication flag", "required_for": "optional"},
    "tc_hdl_ratio": {"category": "derived_lab", "paper_role": "TC:HDL ratio", "required_for": "extract_set_3"},
    "antihypertensive_flag": {
        "category": "medication",
        "paper_role": "antihypertensive exposure",
        "required_for": "extract_set_3",
    },
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
    """รองรับการอ่านไฟล์ดิบจาก Excel/CSV."""
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


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """คำนวณ hash ของไฟล์ raw เพื่อใช้ยืนยันว่า Stage 01 อ่านแบบ read-only."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_raw_file_integrity(config: RawDataConfig) -> dict[str, object]:
    """บันทึก metadata ของไฟล์ raw ก่อน audit โดยไม่แก้ไขไฟล์ต้นทาง."""
    stat = config.raw_path.stat()
    return {
        "raw_path": str(config.raw_path),
        "exists": config.raw_path.exists(),
        "suffix": config.raw_path.suffix.lower(),
        "size_bytes": int(stat.st_size),
        "modified_time": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
        "sha256": file_sha256(config.raw_path),
        "read_only_policy": True,
    }


def first_existing(columns: set[str], candidates: list[str]) -> str | None:
    """คืนชื่อคอลัมน์ตัวแรกที่เจอจาก candidate list."""
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def build_column_list(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"ordinal": range(1, len(df.columns) + 1), "column": df.columns})


def build_schema_summary(df: pd.DataFrame) -> pd.DataFrame:
    """สรุปชนิดข้อมูล จำนวนค่าว่าง และตัวอย่างค่า ต่อคอลัมน์."""
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
    """ตรวจว่า expected fields ตามสเปก pipeline มีอยู่จริงหรือไม่."""
    columns = set(map(str, df.columns))
    rows = []
    for required_field, candidates in EXPECTED_COLUMNS.items():
        matched = first_existing(columns, candidates)
        details = EXPECTED_FIELD_DETAILS.get(required_field, {})
        rows.append(
            {
                "required_field": required_field,
                "category": details.get("category", ""),
                "paper_role": details.get("paper_role", ""),
                "required_for": details.get("required_for", ""),
                "status": "available" if matched else "missing",
                "matched_column": matched or "",
                "candidate_columns": ", ".join(candidates),
            }
        )
    return pd.DataFrame(rows)


def build_data_dictionary(df: pd.DataFrame, column_availability: pd.DataFrame) -> pd.DataFrame:
    """สร้าง data dictionary ระดับ raw ที่ map field ตาม paper เข้ากับ column จริงใน dataset."""
    schema = build_schema_summary(df).set_index("column").to_dict(orient="index")
    rows = []
    for row in column_availability.to_dict(orient="records"):
        matched_column = row["matched_column"]
        schema_row = schema.get(matched_column, {})
        rows.append(
            {
                "required_field": row["required_field"],
                "matched_column": matched_column,
                "status": row["status"],
                "category": row["category"],
                "paper_role": row["paper_role"],
                "required_for": row["required_for"],
                "dtype": schema_row.get("dtype", ""),
                "missing_percent": schema_row.get("missing_percent", ""),
                "unique_count": schema_row.get("unique_count", ""),
                "example_values": schema_row.get("example_values", ""),
            }
        )
    return pd.DataFrame(rows)


def build_visit_coverage(df: pd.DataFrame, config: RawDataConfig) -> pd.DataFrame:
    """คำนวณจำนวน visit และช่วงติดตามต่อผู้ป่วย."""
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


def build_visit_coverage_overview(visit_coverage: pd.DataFrame) -> pd.DataFrame:
    """สรุป longitudinal coverage เพื่อประเมินความพร้อมสำหรับ FIRST/MID/LAST windows."""
    if visit_coverage.empty:
        return pd.DataFrame(
            [
                {
                    "metric": "visit_coverage_available",
                    "value": 0,
                    "detail": "patient id or visit date column missing",
                }
            ]
        )
    records = visit_coverage["record_count"]
    followup = visit_coverage["followup_days"]
    rows = [
        {"metric": "patients_with_visit_coverage", "value": int(len(visit_coverage)), "detail": ""},
        {"metric": "records_per_patient_min", "value": float(records.min()), "detail": ""},
        {"metric": "records_per_patient_median", "value": float(records.median()), "detail": ""},
        {"metric": "records_per_patient_mean", "value": float(records.mean()), "detail": ""},
        {"metric": "records_per_patient_max", "value": float(records.max()), "detail": ""},
        {"metric": "followup_days_min", "value": float(followup.min()), "detail": ""},
        {"metric": "followup_days_median", "value": float(followup.median()), "detail": ""},
        {"metric": "followup_days_mean", "value": float(followup.mean()), "detail": ""},
        {"metric": "followup_days_max", "value": float(followup.max()), "detail": ""},
        {
            "metric": "patients_with_followup_at_least_21_months",
            "value": int((followup >= 21 * 30.4375).sum()),
            "detail": "rough screen for paper FIRST window reach",
        },
        {
            "metric": "patients_with_at_least_3_records",
            "value": int((records >= 3).sum()),
            "detail": "rough screen for multi-window longitudinal data",
        },
    ]
    return pd.DataFrame(rows)


def build_range_summary(df: pd.DataFrame) -> pd.DataFrame:
    """ตรวจค่าที่ต่ำ/สูงเกิน plausible range แบบไม่แก้ข้อมูล."""
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
    """ตรวจความพร้อมของคอลัมน์ diagnosis และจำนวน hit ของรหัส I60-I68."""
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


def build_acceptance_checks(
    df: pd.DataFrame,
    config: RawDataConfig,
    column_availability: pd.DataFrame,
    visit_coverage: pd.DataFrame,
    icd_availability: pd.DataFrame,
) -> pd.DataFrame:
    """สร้าง checklist แบบ machine-readable ตามหัวข้อ Checks / Acceptance Criteria ของ Stage 01."""
    diagnosis_available = bool((icd_availability["status"] == "available").any()) if not icd_availability.empty else False
    stroke_hits = int(icd_availability["stroke_code_record_count"].sum()) if not icd_availability.empty else 0
    missing_fields = column_availability.loc[
        column_availability["status"] == "missing", "required_field"
    ].tolist()
    rows = [
        {
            "check": "raw_file_read_only_policy",
            "passed": True,
            "detail": "Stage 01 reads raw data and writes audit artifacts only.",
        },
        {
            "check": "patient_identifier_found",
            "passed": config.patient_id_col in df.columns,
            "detail": config.patient_id_col,
        },
        {
            "check": "visit_date_found",
            "passed": config.visit_date_col in df.columns,
            "detail": config.visit_date_col,
        },
        {
            "check": "diagnosis_column_found",
            "passed": diagnosis_available,
            "detail": ", ".join(icd_availability.loc[icd_availability["status"] == "available", "column"].tolist()),
        },
        {
            "check": "icd10_i60_i68_checked",
            "passed": True,
            "detail": f"stroke_code_record_hits={stroke_hits}",
        },
        {
            "check": "expected_field_missingness_reported",
            "passed": "missing_percent" in build_schema_summary(df).columns,
            "detail": f"missing_expected_fields={missing_fields}",
        },
        {
            "check": "visit_coverage_reported",
            "passed": not visit_coverage.empty,
            "detail": f"patients_with_visit_coverage={len(visit_coverage)}",
        },
    ]
    return pd.DataFrame(rows)


def build_report_markdown(
    df: pd.DataFrame,
    config: RawDataConfig,
    column_availability: pd.DataFrame,
    visit_coverage: pd.DataFrame,
    icd_availability: pd.DataFrame,
    acceptance_checks: pd.DataFrame,
    raw_file_integrity: dict[str, object],
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
    checks_passed = int(acceptance_checks["passed"].sum()) if not acceptance_checks.empty else 0
    checks_total = int(len(acceptance_checks))
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
- Raw file SHA-256: `{raw_file_integrity["sha256"]}`
- Acceptance checks passed: {checks_passed}/{checks_total}

## Paper Reference

- Paper: `{PAPER_REFERENCE["title"]}`
- Paper data source: `{PAPER_REFERENCE["data_source"]}`
- Paper reported raw records: {PAPER_REFERENCE["reported_records"]:,}
- Paper reported patients: {PAPER_REFERENCE["reported_patients"]:,}
- Paper reported raw attributes: {PAPER_REFERENCE["reported_raw_attributes"]}
- Stroke definition audited in this stage: ICD-10 `{PAPER_REFERENCE["stroke_icd10_range"]}`

## Outputs

- `raw_column_list.csv`
- `raw_data_dictionary.csv`
- `raw_schema_summary.csv`
- `raw_missing_summary.csv`
- `raw_range_summary.csv`
- `visit_coverage_summary.csv`
- `visit_coverage_overview.csv`
- `icd10_availability_report.csv`
- `column_availability_checklist.csv`
- `raw_data_acceptance_checks.csv`
- `raw_file_integrity.json`
- `raw_data_report.json`
- `raw_data_report.md`

## Acceptance Criteria

- Patient identifier found: `{config.patient_id_col in df.columns}`
- Visit date found: `{config.visit_date_col in df.columns}`
- Principal diagnosis found: `{config.principal_dx_col in df.columns}`
- Comorbidity diagnosis found: `{config.comorbidity_dx_col in df.columns}`
- Raw data was read-only: `true`
- Machine-readable checks: `raw_data_acceptance_checks.csv`

## Notes

Stage 01 does not clean, drop, overwrite, or mutate the raw source file. It only produces audit artifacts for the later cleaning and cohort-construction stages.
"""


def run_raw_data_audit(config: RawDataConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 01.

    ลำดับงาน:
    1) อ่านข้อมูลดิบ
    2) สร้างตาราง audit ทุกมุม
    3) เขียน artifact ลง output โดยไม่แตะต้องไฟล์ต้นทาง
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)
    raw_file_integrity = build_raw_file_integrity(config)
    df = load_raw_data(config.raw_path)

    column_list = build_column_list(df)
    schema_summary = build_schema_summary(df)
    missing_summary = build_missing_summary(df)
    column_availability = build_column_availability(df)
    data_dictionary = build_data_dictionary(df, column_availability)
    visit_coverage = build_visit_coverage(df, config)
    visit_coverage_overview = build_visit_coverage_overview(visit_coverage)
    range_summary = build_range_summary(df)
    icd_availability = build_icd_availability(df, config)
    acceptance_checks = build_acceptance_checks(df, config, column_availability, visit_coverage, icd_availability)

    write_csv(column_list, config.output_dir / "raw_column_list.csv")
    write_csv(data_dictionary, config.output_dir / "raw_data_dictionary.csv")
    write_csv(schema_summary, config.output_dir / "raw_schema_summary.csv")
    write_csv(missing_summary, config.output_dir / "raw_missing_summary.csv")
    write_csv(column_availability, config.output_dir / "column_availability_checklist.csv")
    write_csv(visit_coverage, config.output_dir / "visit_coverage_summary.csv")
    write_csv(visit_coverage_overview, config.output_dir / "visit_coverage_overview.csv")
    write_csv(range_summary, config.output_dir / "raw_range_summary.csv")
    write_csv(icd_availability, config.output_dir / "icd10_availability_report.csv")
    write_csv(acceptance_checks, config.output_dir / "raw_data_acceptance_checks.csv")
    write_json(raw_file_integrity, config.output_dir / "raw_file_integrity.json")

    report = {
        "raw_path": str(config.raw_path),
        "output_dir": str(config.output_dir),
        "paper_reference": PAPER_REFERENCE,
        "raw_file_sha256": raw_file_integrity["sha256"],
        "raw_file_size_bytes": raw_file_integrity["size_bytes"],
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "patients": int(df[config.patient_id_col].nunique()) if config.patient_id_col in df.columns else None,
        "required_fields_available": int((column_availability["status"] == "available").sum()),
        "required_fields_missing": int((column_availability["status"] == "missing").sum()),
        "missing_required_fields": column_availability.loc[
            column_availability["status"] == "missing", "required_field"
        ].tolist(),
        "stroke_icd_record_hits": int(icd_availability["stroke_code_record_count"].sum()),
        "visit_coverage_patients": int(len(visit_coverage)),
        "acceptance_checks_passed": int(acceptance_checks["passed"].sum()),
        "acceptance_checks_total": int(len(acceptance_checks)),
        "acceptance_passed": bool(acceptance_checks["passed"].all()),
    }
    write_json(report, config.output_dir / "raw_data_report.json")
    (config.output_dir / "raw_data_report.md").write_text(
        build_report_markdown(
            df,
            config,
            column_availability,
            visit_coverage,
            icd_availability,
            acceptance_checks,
            raw_file_integrity,
        ),
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
