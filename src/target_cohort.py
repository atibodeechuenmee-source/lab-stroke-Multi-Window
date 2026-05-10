"""Stage 02 target and cohort construction.

โมดูลนี้แปลงข้อมูลระดับ visit ให้เป็นชุดวิเคราะห์ระดับ patient:
1) กำหนด label stroke/non-stroke
2) กำหนด reference date ตามกติกา paper
3) ตัดข้อมูลหลัง reference date ทิ้งเพื่อกัน leakage
4) จัด window FIRST/MID/LAST
5) ประเมิน temporal completeness และ attrition
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


STROKE_PATTERN = re.compile(r"\bI6[0-8](?:\.\d+)?\b", re.IGNORECASE)
PAPER_REFERENCE = {
    "title": "Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction",
    "method_section": "Data Selection",
    "stroke_icd10_range": "I60-I68",
    "stroke_reference_rule": "first stroke event date",
    "nonstroke_reference_rule": "last clinical visit date",
    "months_before_reference_formula": "(reference_date - visit_date).days / 30.4375",
}

WINDOWS = {
    "FIRST": (21.0, 9.0),
    "MID": (18.0, 6.0),
    "LAST": (15.0, 3.0),
}
WINDOW_DETAILS = {
    name: {
        "upper_months_before_reference": upper,
        "lower_months_before_reference": lower,
        "inclusive": True,
        "paper_label": f"{int(upper)}-{int(lower)} months before reference date",
    }
    for name, (upper, lower) in WINDOWS.items()
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


def _json_ready(value: Any) -> Any:
    """แปลงค่า pandas/numpy timestamp ให้เขียน JSON ได้ง่ายและอ่านออก."""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _stroke_mask(df: pd.DataFrame, diagnosis_cols: list[str]) -> pd.Series:
    """สร้าง boolean mask ว่าระเบียนไหนมีรหัส stroke I60-I68."""
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
    """จัดประเภทข้อมูลเบื้องต้นและคัดทิ้งแถวที่ขาด patient/date."""
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
    """สร้างตาราง cohort ระดับผู้ป่วยพร้อม target และ reference_date.

    กติกา:
    - stroke=1: reference_date = first_stroke_date
    - stroke=0: reference_date = last_visit_date
    """
    diagnosis_cols = [config.principal_dx_col, config.comorbidity_dx_col]
    working = records.copy()
    working["is_stroke_event"] = _stroke_mask(working, diagnosis_cols)
    working["stroke_event_source"] = ""
    if config.principal_dx_col in working.columns:
        principal_mask = working[config.principal_dx_col].astype(str).str.contains(STROKE_PATTERN, na=False)
        working.loc[principal_mask, "stroke_event_source"] = "principal"
    if config.comorbidity_dx_col in working.columns:
        comorbidity_mask = working[config.comorbidity_dx_col].astype(str).str.contains(STROKE_PATTERN, na=False)
        working.loc[comorbidity_mask & (working["stroke_event_source"] == ""), "stroke_event_source"] = "comorbidity"
        working.loc[comorbidity_mask & (working["stroke_event_source"] == "principal"), "stroke_event_source"] = (
            "principal_and_comorbidity"
        )

    first_stroke = (
        working.loc[working["is_stroke_event"]]
        .groupby(config.patient_id_col)[config.visit_date_col]
        .min()
        .rename("first_stroke_date")
    )
    last_visit = working.groupby(config.patient_id_col)[config.visit_date_col].max().rename("last_visit_date")
    first_visit = working.groupby(config.patient_id_col)[config.visit_date_col].min().rename("first_visit_date")
    record_count = working.groupby(config.patient_id_col).size().rename("record_count")
    stroke_event_count = working.groupby(config.patient_id_col)["is_stroke_event"].sum().rename("stroke_event_count")
    stroke_event_sources = (
        working.loc[working["is_stroke_event"]]
        .groupby(config.patient_id_col)["stroke_event_source"]
        .apply(lambda values: ",".join(sorted(set(filter(None, values.astype(str))))))
        .rename("stroke_event_sources")
    )

    cohort = pd.concat(
        [first_visit, last_visit, record_count, first_stroke, stroke_event_count, stroke_event_sources],
        axis=1,
    ).reset_index()
    cohort["stroke"] = cohort["first_stroke_date"].notna().astype(int)
    cohort["stroke_event_count"] = cohort["stroke_event_count"].fillna(0).astype(int)
    cohort["stroke_event_sources"] = cohort["stroke_event_sources"].fillna("")
    cohort["reference_date"] = cohort["first_stroke_date"].fillna(cohort["last_visit_date"])
    cohort["reference_rule"] = cohort["stroke"].map({1: "first_stroke_date", 0: "last_visit_date"})
    cohort["followup_days_before_reference"] = (cohort["reference_date"] - cohort["first_visit_date"]).dt.days
    return cohort


def build_overlapping_window_records(pre_reference: pd.DataFrame) -> pd.DataFrame:
    """ขยาย records ให้เป็น long format ตาม overlapping FIRST/MID/LAST ของ paper.

    ในงานวิจัย FIRST/MID/LAST ไม่ใช่ bucket ที่แยกขาดจากกัน แต่เป็น temporal windows
    ที่ซ้อนกันได้ เช่น record ที่อยู่ 12 เดือนก่อน reference date จะถูกนับใน FIRST, MID
    และ LAST พร้อมกัน ฟังก์ชันนี้จึงสร้าง 1 แถวต่อ 1 window membership และเก็บ
    `source_record_id` เพื่อ trace กลับไปยัง medical record ต้นฉบับได้เสมอ
    """
    window_rows: list[pd.DataFrame] = []
    matched_source_ids: set[int] = set()

    for window_name, (upper_month, lower_month) in WINDOWS.items():
        mask = pre_reference["months_before_reference"].between(lower_month, upper_month, inclusive="both")
        subset = pre_reference.loc[mask].copy()
        if subset.empty:
            continue
        subset["window"] = window_name
        subset["window_lower_months_before_reference"] = lower_month
        subset["window_upper_months_before_reference"] = upper_month
        window_rows.append(subset)
        matched_source_ids.update(subset["source_record_id"].astype(int).tolist())

    outside = pre_reference.loc[~pre_reference["source_record_id"].isin(matched_source_ids)].copy()
    outside["window"] = pd.NA
    outside["window_lower_months_before_reference"] = pd.NA
    outside["window_upper_months_before_reference"] = pd.NA

    expanded = pd.concat([*window_rows, outside], ignore_index=True) if window_rows else outside.reset_index(drop=True)
    membership_counts = (
        expanded.loc[expanded["window"].notna()]
        .groupby("source_record_id")["window"]
        .nunique()
        .rename("window_membership_count")
    )
    expanded["window_membership_count"] = expanded["source_record_id"].map(membership_counts).fillna(0).astype(int)
    expanded["is_paper_observation_window"] = expanded["window"].notna()
    return expanded.sort_values(["source_record_id", "window"], na_position="last").reset_index(drop=True)


def build_pre_reference_records(
    records: pd.DataFrame, cohort: pd.DataFrame, config: TargetCohortConfig
) -> pd.DataFrame:
    """ตัดเหลือ pre-reference records และคำนวณระยะห่างจาก reference."""
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
    pre_reference = pre_reference.reset_index(drop=True)
    pre_reference.insert(0, "source_record_id", pre_reference.index.astype(int))
    return build_overlapping_window_records(pre_reference)


def build_temporal_completeness(pre_reference: pd.DataFrame, config: TargetCohortConfig) -> pd.DataFrame:
    """ตรวจ completeness ราย patient ว่าผ่านเกณฑ์ทุก window หรือไม่."""
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
        row["core_clinical_column_count_checked"] = int(len(available_core))
        row["temporal_complete"] = temporal_complete
        rows.append(row)

    return pd.DataFrame(rows)


def _source_record_count(df: pd.DataFrame) -> int:
    """นับ medical records ต้นฉบับโดยไม่ให้นับซ้ำจาก overlapping window rows."""
    if "source_record_id" in df.columns:
        return int(df["source_record_id"].nunique())
    return int(len(df))


def build_attrition_report(
    records: pd.DataFrame,
    prepared: pd.DataFrame,
    cohort: pd.DataFrame,
    pre_reference: pd.DataFrame,
    completeness: pd.DataFrame,
    config: TargetCohortConfig,
) -> pd.DataFrame:
    """สรุปการลดลงของ sample size ในแต่ละจุดของ Stage 02."""
    initial_patients = records[config.patient_id_col].nunique() if config.patient_id_col in records.columns else 0
    prepared_patients = prepared[config.patient_id_col].nunique()
    pre_reference_source_records = _source_record_count(pre_reference)
    window_rows = pre_reference.loc[pre_reference["window"].notna()]
    window_source_records = _source_record_count(window_rows)
    post_reference_removed = len(prepared) - pre_reference_source_records
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
            "records_remaining": int(pre_reference_source_records),
            "patients_removed_at_step": 0,
            "records_removed_at_step": int(post_reference_removed),
            "reason": "Remove records after reference date to prevent leakage",
        },
        {
            "step": "has_any_temporal_window_record",
            "patients_remaining": int(window_patient_count),
            "records_remaining": int(window_source_records),
            "patients_removed_at_step": int(pre_reference[config.patient_id_col].nunique() - window_patient_count),
            "records_removed_at_step": int(pre_reference_source_records - window_source_records),
            "reason": "Keep source records assigned to at least one overlapping FIRST/MID/LAST window",
        },
        {
            "step": "overlapping_window_long_format",
            "patients_remaining": int(window_patient_count),
            "records_remaining": int(len(window_rows)),
            "patients_removed_at_step": 0,
            "records_removed_at_step": 0,
            "reason": "Expand eligible source records to one row per overlapping window membership",
        },
        {
            "step": "temporal_complete",
            "patients_remaining": complete_patients,
            "records_remaining": int(
                window_rows[window_rows[config.patient_id_col].isin(
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


def build_reference_date_audit(
    records: pd.DataFrame, cohort: pd.DataFrame, pre_reference: pd.DataFrame, config: TargetCohortConfig
) -> pd.DataFrame:
    """ตรวจ reference date rule และจำนวน records ที่ถูกตัดออกหลัง reference date."""
    total_records_by_patient = (
        records.groupby(config.patient_id_col).size().rename("total_records").reset_index()
    )
    unique_pre_reference = (
        pre_reference.drop_duplicates("source_record_id") if "source_record_id" in pre_reference.columns else pre_reference
    )
    pre_records_by_patient = (
        unique_pre_reference.groupby(config.patient_id_col).size().rename("pre_reference_records").reset_index()
    )
    audit = cohort.merge(total_records_by_patient, on=config.patient_id_col, how="left").merge(
        pre_records_by_patient, on=config.patient_id_col, how="left"
    )
    audit["pre_reference_records"] = audit["pre_reference_records"].fillna(0).astype(int)
    audit["post_reference_records_removed"] = audit["total_records"] - audit["pre_reference_records"]
    audit["reference_rule_valid"] = (
        ((audit["stroke"] == 1) & (audit["reference_date"] == audit["first_stroke_date"]))
        | ((audit["stroke"] == 0) & (audit["reference_date"] == audit["last_visit_date"]))
    )
    return audit[
        [
            config.patient_id_col,
            "stroke",
            "first_visit_date",
            "last_visit_date",
            "first_stroke_date",
            "reference_date",
            "reference_rule",
            "reference_rule_valid",
            "total_records",
            "pre_reference_records",
            "post_reference_records_removed",
            "stroke_event_count",
            "stroke_event_sources",
            "followup_days_before_reference",
        ]
    ]


def build_window_distribution(pre_reference: pd.DataFrame, config: TargetCohortConfig) -> pd.DataFrame:
    """สรุปจำนวน records/patients ใน FIRST/MID/LAST และ records นอก window."""
    rows = []
    for window_name in list(WINDOWS) + ["OUTSIDE_WINDOWS"]:
        if window_name == "OUTSIDE_WINDOWS":
            subset = pre_reference[pre_reference["window"].isna()]
            lower = ""
            upper = ""
        else:
            subset = pre_reference[pre_reference["window"] == window_name]
            upper, lower = WINDOWS[window_name]
        rows.append(
            {
                "window": window_name,
                "lower_months_before_reference": lower,
                "upper_months_before_reference": upper,
                "records": int(len(subset)),
                "source_records": _source_record_count(subset),
                "patients": int(subset[config.patient_id_col].nunique()) if config.patient_id_col in subset.columns else 0,
                "stroke_patients": int(
                    subset.loc[subset["stroke"] == 1, config.patient_id_col].nunique()
                )
                if "stroke" in subset.columns and config.patient_id_col in subset.columns
                else 0,
                "nonstroke_patients": int(
                    subset.loc[subset["stroke"] == 0, config.patient_id_col].nunique()
                )
                if "stroke" in subset.columns and config.patient_id_col in subset.columns
                else 0,
            }
        )
    return pd.DataFrame(rows)


def build_window_membership_report(pre_reference: pd.DataFrame) -> pd.DataFrame:
    """สรุปว่า medical record ต้นฉบับหนึ่งแถวถูกใช้ในกี่ overlapping windows."""
    if "source_record_id" not in pre_reference.columns:
        return pd.DataFrame()
    membership = (
        pre_reference.drop_duplicates("source_record_id")
        ["window_membership_count"]
        .value_counts(dropna=False)
        .sort_index()
        .rename_axis("window_membership_count")
        .reset_index(name="source_records")
    )
    membership["meaning"] = membership["window_membership_count"].map(
        {
            0: "outside FIRST/MID/LAST observation windows",
            1: "belongs to one paper window",
            2: "belongs to two overlapping paper windows",
            3: "belongs to all FIRST/MID/LAST windows",
        }
    )
    return membership


def build_temporal_completeness_summary(completeness: pd.DataFrame) -> pd.DataFrame:
    """สรุป completeness ราย window และจำนวนผู้ป่วยที่ผ่านเกณฑ์ paper strict windows."""
    if completeness.empty:
        return pd.DataFrame(
            [{"metric": "temporal_complete_patients", "value": 0, "detail": "no patients in pre-reference records"}]
        )
    rows = [{"metric": "patients_checked", "value": int(len(completeness)), "detail": ""}]
    for window_name in WINDOWS:
        prefix = window_name.lower()
        rows.extend(
            [
                {
                    "metric": f"{prefix}_has_visit_patients",
                    "value": int(completeness[f"{prefix}_has_visit"].sum()),
                    "detail": "",
                },
                {
                    "metric": f"{prefix}_has_core_clinical_patients",
                    "value": int(completeness[f"{prefix}_has_core_clinical"].sum()),
                    "detail": "",
                },
            ]
        )
    rows.append(
        {
            "metric": "temporal_complete_patients",
            "value": int(completeness["temporal_complete"].sum()),
            "detail": "visit and core clinical coverage in FIRST, MID, LAST",
        }
    )
    return pd.DataFrame(rows)


def build_acceptance_checks(
    cohort: pd.DataFrame,
    pre_reference: pd.DataFrame,
    completeness: pd.DataFrame,
    attrition: pd.DataFrame,
    config: TargetCohortConfig,
) -> pd.DataFrame:
    """สร้าง acceptance checks ตาม docs/pipeline/02-target-and-cohort.md."""
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
    observed_windows = set(pre_reference["window"].dropna().astype(str).unique().tolist())
    expected_windows = set(WINDOWS.keys())
    temporal_complete_reported = "temporal_complete" in completeness.columns
    attrition_has_temporal_step = bool(
        not attrition.empty and "temporal_complete" in attrition["step"].astype(str).tolist()
    )
    overlapping_supported = bool(
        "window_membership_count" in pre_reference.columns
        and (pre_reference["window_membership_count"] > 1).any()
    )
    rows = [
        {
            "check": "stroke_reference_is_first_stroke_date",
            "passed": stroke_reference_ok,
            "detail": PAPER_REFERENCE["stroke_reference_rule"],
        },
        {
            "check": "nonstroke_reference_is_last_visit_date",
            "passed": nonstroke_reference_ok,
            "detail": PAPER_REFERENCE["nonstroke_reference_rule"],
        },
        {
            "check": "no_post_reference_records",
            "passed": no_post_reference,
            "detail": "all output records must have visit_date <= reference_date",
        },
        {
            "check": "paper_default_windows_used",
            "passed": expected_windows.issubset(observed_windows),
            "detail": f"observed={sorted(observed_windows)} expected={sorted(expected_windows)}",
        },
        {
            "check": "overlapping_window_membership_supported",
            "passed": overlapping_supported,
            "detail": "one source medical record can appear in multiple FIRST/MID/LAST rows",
        },
        {
            "check": "attrition_reports_temporal_completeness",
            "passed": attrition_has_temporal_step,
            "detail": "cohort_attrition_report.csv includes temporal_complete step",
        },
        {
            "check": "temporal_complete_cohort_reported",
            "passed": temporal_complete_reported,
            "detail": f"temporal_complete_patients={int(completeness['temporal_complete'].sum()) if temporal_complete_reported and not completeness.empty else 0}",
        },
    ]
    return pd.DataFrame(rows)


def build_quality_checks(
    cohort: pd.DataFrame, pre_reference: pd.DataFrame, completeness: pd.DataFrame, config: TargetCohortConfig
) -> dict[str, object]:
    """ตรวจ invariant สำคัญ: ไม่มี post-reference และ reference rule ถูกต้อง."""
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
        "paper_reference": PAPER_REFERENCE,
        "temporal_windows": WINDOW_DETAILS,
        "no_post_reference_records": no_post_reference,
        "stroke_reference_is_first_stroke_date": stroke_reference_ok,
        "nonstroke_reference_is_last_visit_date": nonstroke_reference_ok,
        "patients": int(len(cohort)),
        "stroke_patients": int(cohort["stroke"].sum()),
        "nonstroke_patients": int((cohort["stroke"] == 0).sum()),
        "pre_reference_source_records": _source_record_count(pre_reference),
        "pre_reference_rows_after_window_expansion": int(len(pre_reference)),
        "paper_observation_window_rows": int(pre_reference["window"].notna().sum()),
        "temporal_complete_patients": int(completeness["temporal_complete"].sum()) if not completeness.empty else 0,
    }


def build_markdown_report(
    report: dict[str, object],
    config: TargetCohortConfig,
    acceptance_checks: pd.DataFrame,
    window_distribution: pd.DataFrame,
) -> str:
    checks_passed = int(acceptance_checks["passed"].sum()) if not acceptance_checks.empty else 0
    checks_total = int(len(acceptance_checks))
    first_mid_last_rows = int(
        window_distribution.loc[
            window_distribution["window"].isin(WINDOWS.keys()), "records"
        ].sum()
    ) if not window_distribution.empty else 0
    first_mid_last_source_records = int(
        window_distribution.loc[
            window_distribution["window"].isin(WINDOWS.keys()), "source_records"
        ].sum()
    ) if not window_distribution.empty and "source_records" in window_distribution.columns else 0
    return f"""# Target and Cohort Report

## Summary

- Input: `{config.input_path}`
- Patients: {report["patients"]:,}
- Stroke patients: {report["stroke_patients"]:,}
- Non-stroke patients: {report["nonstroke_patients"]:,}
- Pre-reference source records: {report["pre_reference_source_records"]:,}
- Rows after overlapping window expansion: {report["pre_reference_rows_after_window_expansion"]:,}
- Temporal-complete patients: {report["temporal_complete_patients"]:,}
- FIRST/MID/LAST window membership rows: {first_mid_last_rows:,}
- FIRST/MID/LAST source-record memberships: {first_mid_last_source_records:,}
- Acceptance checks passed: {checks_passed}/{checks_total}

## Paper Reference

- Paper: `{PAPER_REFERENCE["title"]}`
- Method section: `{PAPER_REFERENCE["method_section"]}`
- Stroke definition: ICD-10 `{PAPER_REFERENCE["stroke_icd10_range"]}`
- Months before reference: `{PAPER_REFERENCE["months_before_reference_formula"]}`

## Reference Date Rules

- Stroke patient: first stroke event date from ICD-10 `I60-I68`
- Non-stroke patient: last clinical visit date
- All records after reference date are removed before window assignment

## Temporal Windows

- FIRST: 21-9 months before reference date
- MID: 18-6 months before reference date
- LAST: 15-3 months before reference date
- Windows are overlapping. A single medical record can be emitted into more than one window row.

## Quality Checks

- No post-reference records: `{report["no_post_reference_records"]}`
- Stroke reference is first stroke date: `{report["stroke_reference_is_first_stroke_date"]}`
- Non-stroke reference is last visit date: `{report["nonstroke_reference_is_last_visit_date"]}`

## Outputs

- `patient_level_cohort.csv`
- `pre_reference_records_with_windows.csv`
- `temporal_completeness_flags.csv`
- `temporal_completeness_summary.csv`
- `cohort_attrition_report.csv`
- `reference_date_audit.csv`
- `window_distribution_report.csv`
- `window_membership_report.csv`
- `target_cohort_acceptance_checks.csv`
- `target_cohort_summary.json`
- `target_cohort_report.md`
"""


def run_target_cohort(config: TargetCohortConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 02."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(config.input_path)
    prepared = prepare_records(records, config)
    cohort = build_patient_cohort(prepared, config)
    pre_reference = build_pre_reference_records(prepared, cohort, config)
    completeness = build_temporal_completeness(pre_reference, config)
    attrition = build_attrition_report(records, prepared, cohort, pre_reference, completeness, config)
    reference_audit = build_reference_date_audit(prepared, cohort, pre_reference, config)
    window_distribution = build_window_distribution(pre_reference, config)
    window_membership = build_window_membership_report(pre_reference)
    completeness_summary = build_temporal_completeness_summary(completeness)
    acceptance_checks = build_acceptance_checks(cohort, pre_reference, completeness, attrition, config)
    report = build_quality_checks(cohort, pre_reference, completeness, config)
    report.update(
        {
            "reference_date_audit_passed": bool(reference_audit["reference_rule_valid"].all()),
            "records_in_paper_windows": int(
                window_distribution.loc[
                    window_distribution["window"].isin(WINDOWS.keys()), "records"
                ].sum()
            ),
            "source_records_in_any_paper_window": int(
                pre_reference.loc[pre_reference["window"].notna(), "source_record_id"].nunique()
                if "source_record_id" in pre_reference.columns
                else pre_reference["window"].notna().sum()
            ),
            "source_records_with_multiple_window_memberships": int(
                pre_reference.drop_duplicates("source_record_id")["window_membership_count"].gt(1).sum()
                if {"source_record_id", "window_membership_count"}.issubset(pre_reference.columns)
                else 0
            ),
            "patients_in_any_paper_window": int(
                pre_reference.loc[pre_reference["window"].notna(), config.patient_id_col].nunique()
            ),
            "acceptance_checks_passed": int(acceptance_checks["passed"].sum()),
            "acceptance_checks_total": int(len(acceptance_checks)),
            "acceptance_passed": bool(acceptance_checks["passed"].all()),
        }
    )
    report = {key: _json_ready(value) for key, value in report.items()}

    write_csv(cohort, config.output_dir / "patient_level_cohort.csv")
    write_csv(pre_reference, config.output_dir / "pre_reference_records_with_windows.csv")
    write_csv(completeness, config.output_dir / "temporal_completeness_flags.csv")
    write_csv(completeness_summary, config.output_dir / "temporal_completeness_summary.csv")
    write_csv(attrition, config.output_dir / "cohort_attrition_report.csv")
    write_csv(reference_audit, config.output_dir / "reference_date_audit.csv")
    write_csv(window_distribution, config.output_dir / "window_distribution_report.csv")
    write_csv(window_membership, config.output_dir / "window_membership_report.csv")
    write_csv(acceptance_checks, config.output_dir / "target_cohort_acceptance_checks.csv")
    write_json(report, config.output_dir / "target_cohort_summary.json")
    (config.output_dir / "target_cohort_report.md").write_text(
        build_markdown_report(report, config, acceptance_checks, window_distribution), encoding="utf-8"
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
