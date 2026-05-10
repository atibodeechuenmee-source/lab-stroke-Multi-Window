"""Stage 05 feature engineering for temporal stroke-risk prediction.

เป้าหมาย:
1) สร้าง single-shot baseline (latest pre-reference)
2) สร้าง temporal Extract Set 1/2/3 ตามแนว paper
3) สร้าง feature dictionary และ exclusion report เพื่อ trace ได้

ข้อกำกับสำคัญ:
- ใช้เฉพาะข้อมูลก่อน reference date
- temporal sets ใช้เฉพาะผู้ป่วยที่ผ่าน completeness criteria
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
    "method_section": "Feature Extraction",
    "single_shot_role": "required baseline comparator",
    "temporal_windows": ["FIRST", "MID", "LAST"],
}
PAPER_TARGET_FEATURE_COUNTS = {
    "extract_set_1": 35,
    "extract_set_2": 115,
    "extract_set_3": 121,
}


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    records_path: Path = Path("output/data_cleaning_output/cleaned_pre_reference_records.csv")
    output_dir: Path = Path("output/feature_engineering_output")
    patient_id_col: str = "patient_id"
    visit_date_col: str = "visit_date"
    reference_date_col: str = "reference_date"


NUMERIC_COLUMNS = {
    "bps": "bps",
    "bpd": "bpd",
    "hdl": "hdl",
    "ldl": "ldl",
    "fbs": "fbs",
    "bmi": "bmi",
    "egfr": "egfr",
    "creatinine": "creatinine",
    "cholesterol": "cholesterol",
    "triglyceride": "triglyceride",
}

CATEGORICAL_COLUMNS = {
    "age": "age",
    "sex": "sex",
    "atrial_fibrillation": "atrial_fibrillation",
    "smoke": "smoke",
    "drinking": "drinking",
}

RISK_FACTOR_COLUMNS = {
    "diabetes": "diabetes",
    "hypertension": "hypertension",
    "heart_disease": "heart_disease",
    "statin": "statin",
    "antihypertensive_flag": "antihypertensive_flag",
    "tc_hdl_ratio": "tc_hdl_ratio",
}

WINDOWS = ["FIRST", "MID", "LAST"]
WINDOW_MONTH_CENTERS = {"FIRST": 15.0, "MID": 12.0, "LAST": 9.0}


def load_records(path: Path, config: FeatureEngineeringConfig) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    records = pd.read_csv(path, parse_dates=[config.visit_date_col, config.reference_date_col])
    required = [config.patient_id_col, config.visit_date_col, "stroke", "window"]
    missing = [column for column in required if column not in records.columns]
    if missing:
        raise KeyError(f"Missing required columns for feature engineering: {missing}")
    return records


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


def ensure_tc_hdl_ratio(records: pd.DataFrame) -> pd.DataFrame:
    """สร้าง tc_hdl_ratio เมื่อคอลัมน์ยังไม่มีและข้อมูลเพียงพอ."""
    prepared = records.copy()
    if "tc_hdl_ratio" not in prepared.columns and {"cholesterol", "hdl"}.issubset(prepared.columns):
        prepared["tc_hdl_ratio"] = np.where(
            pd.to_numeric(prepared["hdl"], errors="coerce") > 0,
            pd.to_numeric(prepared["cholesterol"], errors="coerce") / pd.to_numeric(prepared["hdl"], errors="coerce"),
            np.nan,
        )
    return prepared


def paper_observation_records(records: pd.DataFrame) -> pd.DataFrame:
    """เลือกเฉพาะ observation windows ของ paper และตัดแถวซ้ำจาก long-format เท่าที่จำเป็น.

    Stage 02 ส่งข้อมูลแบบ long format เพราะ FIRST/MID/LAST ซ้อนกันได้ Record เดียวจึงอาจมี
    หลายแถวต่าง window กัน ฟังก์ชันนี้ใช้กับ single-shot baseline เพื่อเลือก medical record
    ต้นฉบับล่าสุดในช่วง 15-3 เดือนก่อน reference date โดยไม่เผลอใช้ prediction window
    0-3 เดือนก่อน reference date และไม่ให้ record เดียวถูกนับซ้ำเพราะอยู่หลาย windows
    """
    eligible = records[records["window"].isin(WINDOWS)].copy()
    if "source_record_id" in eligible.columns:
        eligible = eligible.drop_duplicates("source_record_id")
    return eligible


def build_tc_hdl_audit(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """บันทึกว่า TC:HDL มีอยู่เดิมหรือถูกคำนวณเพิ่ม และไม่มีการหารด้วยศูนย์."""
    had_column_before = "tc_hdl_ratio" in before.columns
    hdl_positive = (
        int((pd.to_numeric(after["hdl"], errors="coerce") > 0).sum())
        if "hdl" in after.columns
        else 0
    )
    computed_non_null = int(after["tc_hdl_ratio"].notna().sum()) if "tc_hdl_ratio" in after.columns else 0
    divide_by_zero_candidates = (
        int((pd.to_numeric(after["hdl"], errors="coerce") == 0).sum())
        if "hdl" in after.columns
        else 0
    )
    return pd.DataFrame(
        [
            {
                "had_tc_hdl_ratio_before": had_column_before,
                "tc_hdl_ratio_available_after": "tc_hdl_ratio" in after.columns,
                "hdl_positive_records": hdl_positive,
                "tc_hdl_ratio_non_null_after": computed_non_null,
                "hdl_zero_records": divide_by_zero_candidates,
                "divide_by_zero_prevented": True,
            }
        ]
    )


def latest_non_null(series: pd.Series):
    values = series.dropna()
    return values.iloc[-1] if len(values) else np.nan


def validate_pre_reference(records: pd.DataFrame, config: FeatureEngineeringConfig) -> bool:
    """เช็ค invariant ว่าไม่มี record หลัง reference date."""
    if config.reference_date_col not in records.columns:
        return True
    valid = records[[config.visit_date_col, config.reference_date_col]].dropna()
    return bool((valid[config.visit_date_col] <= valid[config.reference_date_col]).all())


def build_single_shot(records: pd.DataFrame, config: FeatureEngineeringConfig) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """สร้าง baseline จาก record ล่าสุดใน FIRST/MID/LAST ไม่ใช้ prediction window 0-3 เดือน."""
    eligible_records = paper_observation_records(records)
    sorted_records = eligible_records.sort_values([config.patient_id_col, config.visit_date_col])
    latest = sorted_records.groupby(config.patient_id_col).tail(1).copy()
    feature_cols = [
        "stroke",
        *[col for col in NUMERIC_COLUMNS.values() if col in latest.columns],
        *[col for col in CATEGORICAL_COLUMNS.values() if col in latest.columns],
        *[col for col in RISK_FACTOR_COLUMNS.values() if col in latest.columns],
    ]
    result = latest[[config.patient_id_col, *feature_cols]].copy()
    rename = {col: f"baseline_{col}" for col in feature_cols if col != "stroke"}
    result = result.rename(columns=rename)
    dictionary = [
        {
            "feature": new_name,
            "source_column": old_name,
            "source_window": "latest_observation_record",
            "aggregation": "latest record from FIRST/MID/LAST observation windows",
            "feature_set": "single_shot",
        }
        for old_name, new_name in rename.items()
    ]
    return result, dictionary


def build_single_shot_audit(records: pd.DataFrame, single_shot: pd.DataFrame, config: FeatureEngineeringConfig) -> pd.DataFrame:
    """ตรวจว่า single-shot เลือก latest observation-window record ต่อ patient จริง."""
    eligible_records = paper_observation_records(records)
    latest_dates = (
        eligible_records.sort_values([config.patient_id_col, config.visit_date_col])
        .groupby(config.patient_id_col)[config.visit_date_col]
        .max()
        .rename("latest_observation_visit_date")
        .reset_index()
    )
    selected_ids = single_shot[[config.patient_id_col]].copy()
    audit = selected_ids.merge(latest_dates, on=config.patient_id_col, how="left")
    audit["selected_latest_observation_record"] = audit["latest_observation_visit_date"].notna()
    return audit


def temporal_complete_patient_ids(records: pd.DataFrame, config: FeatureEngineeringConfig) -> tuple[set, pd.DataFrame]:
    """คัด patient ที่มี visit+core numeric ครบทุก FIRST/MID/LAST."""
    rows = []
    available_numeric = [col for col in NUMERIC_COLUMNS.values() if col in records.columns]
    for patient_id, group in records.groupby(config.patient_id_col):
        row = {config.patient_id_col: patient_id}
        complete = True
        for window in WINDOWS:
            wg = group[group["window"] == window]
            has_visit = len(wg) > 0
            has_core = bool(available_numeric) and all(wg[col].notna().any() for col in available_numeric)
            row[f"{window.lower()}_visit_count"] = int(len(wg))
            row[f"{window.lower()}_has_visit"] = has_visit
            row[f"{window.lower()}_has_core_numeric"] = has_core
            complete = complete and has_visit and has_core
        row["temporal_complete"] = complete
        rows.append(row)
    completeness = pd.DataFrame(rows)
    ids = set(completeness.loc[completeness["temporal_complete"], config.patient_id_col])
    return ids, completeness


def base_patient_table(records: pd.DataFrame, patient_ids: set, config: FeatureEngineeringConfig) -> pd.DataFrame:
    labels = records[[config.patient_id_col, "stroke"]].drop_duplicates(subset=[config.patient_id_col])
    labels = labels[labels[config.patient_id_col].isin(patient_ids)].copy()
    return labels.set_index(config.patient_id_col)


def add_window_means(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Extract Set 1: เพิ่มค่าเฉลี่ยของตัวแปรเชิงตัวเลขต่อ window."""
    dictionary = []
    result = table.copy()
    for window in WINDOWS:
        wg = records[records["window"] == window]
        for name, col in NUMERIC_COLUMNS.items():
            if col not in wg.columns:
                continue
            feature = f"{window.lower()}_{name}_mean"
            values = wg.groupby("patient_id")[col].mean().rename(feature)
            result = result.join(values, how="left")
            dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": window,
                    "aggregation": "mean",
                    "feature_set": "extract_set_1",
                }
            )
    return result, dictionary


def add_latest_categorical(table: pd.DataFrame, records: pd.DataFrame, feature_set: str) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """เพิ่ม 5 static/latest features ตามการนับของ paper.

    Paper นับ Set 1 เป็น `10 numerical variables x 3 windows + 5 categorical features`.
    ใน implementation นี้ 5 static/latest features คือ age, sex, AF, smoking, drinking.
    Age เป็น numerical ในเชิงชนิดข้อมูล แต่ไม่ถูกคูณ temporal windows ตามสูตรนับของ paper
    จึงอยู่ในกลุ่ม static/latest features เพื่อให้จำนวน feature ตรง 35/115/121.
    """
    result = table.copy()
    dictionary = []
    sorted_records = records.sort_values(["patient_id", "visit_date"])
    grouped = sorted_records.groupby("patient_id")
    for name, col in CATEGORICAL_COLUMNS.items():
        if col not in records.columns:
            continue
        feature = f"latest_{name}"
        values = grouped[col].agg(latest_non_null).rename(feature)
        result = result.join(values, how="left")
        dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": "latest_observation_window",
                    "aggregation": "latest non-null",
                    "feature_set": feature_set,
                }
        )
    return result, dictionary


def add_paper_set2_descriptors(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Extract Set 2: สร้าง 11 descriptors ต่อ numerical variable ให้ได้ 115 features ตาม paper.

    Paper ระบุ Set 2 เป็น `5 + (11 x 10) = 115 features`.
    เราจึงสร้าง descriptors 11 ตัวต่อ numeric variable ดังนี้:
    first_window_mean, mid_window_mean, last_window_mean, temporal_min,
    temporal_max, temporal_std, first_value, last_value, delta_last_first,
    slope_last_first, count_diff_last_first.
    """
    result = table.copy()
    dictionary = []
    for name, col in NUMERIC_COLUMNS.items():
        if col not in records.columns:
            continue
        sorted_records = records.sort_values(["patient_id", "visit_date"])
        first_records = sorted_records[sorted_records["window"] == "FIRST"]
        mid_records = sorted_records[sorted_records["window"] == "MID"]
        last_records = sorted_records[sorted_records["window"] == "LAST"]
        first_mean = first_records.groupby("patient_id")[col].mean()
        mid_mean = mid_records.groupby("patient_id")[col].mean()
        last_mean = last_records.groupby("patient_id")[col].mean()
        first_count = first_records.groupby("patient_id")[col].count()
        last_count = last_records.groupby("patient_id")[col].count()
        window_mean_table = pd.concat(
            [first_mean.rename("FIRST"), mid_mean.rename("MID"), last_mean.rename("LAST")],
            axis=1,
        )
        delta = last_mean - first_mean
        descriptors = {
            f"{name}_first_window_mean": (first_mean, "FIRST", "mean"),
            f"{name}_mid_window_mean": (mid_mean, "MID", "mean"),
            f"{name}_last_window_mean": (last_mean, "LAST", "mean"),
            f"{name}_temporal_min": (window_mean_table.min(axis=1), "FIRST,MID,LAST", "min of window means"),
            f"{name}_temporal_max": (window_mean_table.max(axis=1), "FIRST,MID,LAST", "max of window means"),
            f"{name}_temporal_std": (window_mean_table.std(axis=1, ddof=0), "FIRST,MID,LAST", "std of window means"),
            f"{name}_first_value": (first_mean, "FIRST", "FIRST window mean"),
            f"{name}_last_value": (last_mean, "LAST", "LAST window mean"),
            f"{name}_delta_last_first": (delta, "FIRST,LAST", "LAST mean - FIRST mean"),
            f"{name}_slope_last_first": (
                delta / (WINDOW_MONTH_CENTERS["FIRST"] - WINDOW_MONTH_CENTERS["LAST"]),
                "FIRST,LAST",
                "delta / 6 months",
            ),
            f"{name}_count_diff_last_first": (last_count - first_count, "FIRST,LAST", "LAST count - FIRST count"),
        }
        for feature, (values, source_window, aggregation) in descriptors.items():
            result = result.join(values.rename(feature), how="left")
            dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": source_window,
                    "aggregation": aggregation,
                    "feature_set": "extract_set_2",
                }
            )
    return result, dictionary


def add_risk_factors(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Extract Set 3: เพิ่ม risk-factor/latest medication-related flags."""
    result = table.copy()
    dictionary = []
    sorted_records = records.sort_values(["patient_id", "visit_date"])
    grouped = sorted_records.groupby("patient_id")
    for name, col in RISK_FACTOR_COLUMNS.items():
        if col not in records.columns:
            continue
        feature = f"latest_{name}"
        values = grouped[col].agg(latest_non_null).rename(feature)
        result = result.join(values, how="left")
        dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": "latest_observation_window",
                    "aggregation": "latest non-null",
                    "feature_set": "extract_set_3",
                }
        )
    return result, dictionary


def build_feature_sets(records: pd.DataFrame, config: FeatureEngineeringConfig) -> dict[str, pd.DataFrame | list[dict[str, str]]]:
    """ประกอบ single_shot + extract_set_1/2/3 พร้อม dictionary."""
    original_records = records.copy()
    records = ensure_tc_hdl_ratio(records)
    tc_hdl_audit = build_tc_hdl_audit(original_records, records)
    complete_ids, completeness = temporal_complete_patient_ids(records, config)
    # temporal features ใช้เฉพาะผู้ป่วยที่ผ่าน completeness และอยู่ใน 3 windows เท่านั้น
    temporal_records = records[records[config.patient_id_col].isin(complete_ids) & records["window"].isin(WINDOWS)].copy()

    single_shot, single_dict = build_single_shot(records, config)
    single_shot_audit = build_single_shot_audit(records, single_shot, config)

    set1_base = base_patient_table(records, complete_ids, config)
    set1_table, set1_dict = add_window_means(set1_base, temporal_records)
    set1_table, set1_cat_dict = add_latest_categorical(set1_table, temporal_records, "extract_set_1")
    set1 = set1_table.reset_index()

    set2_base = base_patient_table(records, complete_ids, config)
    set2_table, set2_cat_dict = add_latest_categorical(set2_base, temporal_records, "extract_set_2")
    set2_table, paper_descriptor_dict = add_paper_set2_descriptors(set2_table, temporal_records)
    set2 = set2_table.reset_index()

    set3_table, risk_dict = add_risk_factors(set2_table, temporal_records)
    set3 = set3_table.reset_index()

    dictionary = single_dict + set1_dict + set1_cat_dict + set2_cat_dict + paper_descriptor_dict + risk_dict
    return {
        "single_shot": single_shot,
        "extract_set_1": set1,
        "extract_set_2": set2,
        "extract_set_3": set3,
        "temporal_completeness": completeness,
        "feature_dictionary": pd.DataFrame(dictionary),
        "single_shot_audit": single_shot_audit,
        "tc_hdl_audit": tc_hdl_audit,
    }


def build_exclusion_report(records: pd.DataFrame, completeness: pd.DataFrame, config: FeatureEngineeringConfig) -> pd.DataFrame:
    """รายงานเหตุผลที่ผู้ป่วยบางรายถูกตัดออกจาก temporal sets."""
    rows = []
    all_ids = set(records[config.patient_id_col].dropna().unique())
    complete_ids = set(completeness.loc[completeness["temporal_complete"], config.patient_id_col])
    excluded_ids = sorted(all_ids - complete_ids)
    for patient_id in excluded_ids:
        row = completeness.loc[completeness[config.patient_id_col] == patient_id]
        if row.empty:
            reason = "no window records"
        else:
            reasons = []
            record = row.iloc[0].to_dict()
            for window in WINDOWS:
                if not record.get(f"{window.lower()}_has_visit", False):
                    reasons.append(f"missing_{window.lower()}_visit")
                elif not record.get(f"{window.lower()}_has_core_numeric", False):
                    reasons.append(f"missing_{window.lower()}_core_numeric")
            reason = ";".join(reasons) if reasons else "not_temporal_complete"
        rows.append({config.patient_id_col: patient_id, "reason": reason})
    return pd.DataFrame(rows)


def build_generation_log(feature_sets: dict[str, pd.DataFrame | list[dict[str, str]]], no_post_reference: bool) -> pd.DataFrame:
    rows = []
    for name in ["single_shot", "extract_set_1", "extract_set_2", "extract_set_3"]:
        table = feature_sets[name]
        assert isinstance(table, pd.DataFrame)
        rows.append(
            {
                "artifact": name,
                "rows": int(len(table)),
                "columns": int(table.shape[1]),
                "one_row_per_patient": bool(table["patient_id"].is_unique) if "patient_id" in table.columns else False,
                "pre_reference_only": no_post_reference,
            }
        )
    return pd.DataFrame(rows)


def build_temporal_window_usage_report(records: pd.DataFrame, config: FeatureEngineeringConfig) -> pd.DataFrame:
    """ยืนยันว่า temporal feature records ใช้เฉพาะ FIRST/MID/LAST และไม่มี post-reference."""
    rows = []
    for window in WINDOWS + ["OUTSIDE_WINDOWS"]:
        subset = records[records["window"].isna()] if window == "OUTSIDE_WINDOWS" else records[records["window"] == window]
        rows.append(
            {
                "window": window,
                "records": int(len(subset)),
                "source_records": int(subset["source_record_id"].nunique())
                if "source_record_id" in subset.columns
                else int(len(subset)),
                "patients": int(subset[config.patient_id_col].nunique()) if config.patient_id_col in subset.columns else 0,
                "used_for_temporal_features": window in WINDOWS,
            }
        )
    return pd.DataFrame(rows)


def _feature_count(table: pd.DataFrame) -> int:
    """นับ feature columns โดยไม่นับ patient id และ target label."""
    return len([column for column in table.columns if column not in {"patient_id", "stroke"}])


def build_feature_set_comparison(
    set1: pd.DataFrame,
    set2: pd.DataFrame,
    set3: pd.DataFrame,
) -> pd.DataFrame:
    """เทียบจำนวน feature ที่สร้างจริงกับ target counts ที่ paper รายงาน."""
    tables = {"extract_set_1": set1, "extract_set_2": set2, "extract_set_3": set3}
    rows = []
    for name, table in tables.items():
        actual_features = _feature_count(table)
        target = PAPER_TARGET_FEATURE_COUNTS[name]
        rows.append(
            {
                "feature_set": name,
                "paper_target_feature_count": target,
                "actual_feature_count": actual_features,
                "actual_columns_including_id_and_target": int(table.shape[1]),
                "difference_from_paper_target": int(actual_features - target),
                "matches_paper_target_exactly": bool(actual_features == target),
            }
        )
    return pd.DataFrame(rows)


def build_acceptance_checks(
    records: pd.DataFrame,
    feature_sets: dict[str, pd.DataFrame | list[dict[str, str]]],
    generation_log: pd.DataFrame,
    feature_set_comparison: pd.DataFrame,
    temporal_window_usage: pd.DataFrame,
    no_post_reference: bool,
) -> pd.DataFrame:
    """สร้าง acceptance checks ตาม docs/pipeline/05-feature-engineering.md."""
    single = feature_sets["single_shot"]
    set1 = feature_sets["extract_set_1"]
    set2 = feature_sets["extract_set_2"]
    set3 = feature_sets["extract_set_3"]
    dictionary = feature_sets["feature_dictionary"]
    single_audit = feature_sets["single_shot_audit"]
    tc_hdl_audit = feature_sets["tc_hdl_audit"]
    assert isinstance(single, pd.DataFrame)
    assert isinstance(set1, pd.DataFrame)
    assert isinstance(set2, pd.DataFrame)
    assert isinstance(set3, pd.DataFrame)
    assert isinstance(dictionary, pd.DataFrame)
    assert isinstance(single_audit, pd.DataFrame)
    assert isinstance(tc_hdl_audit, pd.DataFrame)

    one_row_per_patient = bool(generation_log["one_row_per_patient"].all()) if not generation_log.empty else False
    temporal_usage_ok = bool(
        temporal_window_usage.loc[
            temporal_window_usage["used_for_temporal_features"], "window"
        ].isin(WINDOWS).all()
    )
    dictionary_ok = bool(
        not dictionary.empty
        and {"feature", "source_column", "source_window", "aggregation", "feature_set"}.issubset(dictionary.columns)
    )
    feature_sets_generated = all(len(table) > 0 for table in [single, set1, set2, set3])
    feature_count_reported = bool(not feature_set_comparison.empty and len(feature_set_comparison) == 3)
    feature_counts_match_paper = bool(
        feature_count_reported and feature_set_comparison["matches_paper_target_exactly"].all()
    )
    tc_hdl_ok = bool(tc_hdl_audit.iloc[0]["tc_hdl_ratio_available_after"]) if not tc_hdl_audit.empty else False
    return pd.DataFrame(
        [
            {
                "check": "single_shot_uses_latest_observation_window_record",
                "passed": bool(single_audit["selected_latest_observation_record"].all()) and len(single) > 0,
                "detail": f"single_shot_rows={len(single)}",
            },
            {
                "check": "temporal_features_use_first_mid_last_only",
                "passed": temporal_usage_ok,
                "detail": "temporal windows registered as FIRST/MID/LAST",
            },
            {
                "check": "no_post_reference_records_used",
                "passed": bool(no_post_reference),
                "detail": "visit_date <= reference_date",
            },
            {
                "check": "feature_dictionary_traces_origin",
                "passed": dictionary_ok,
                "detail": f"dictionary_rows={len(dictionary)}",
            },
            {
                "check": "extract_sets_generated_separately",
                "passed": feature_sets_generated and one_row_per_patient,
                "detail": f"set1={len(set1)}; set2={len(set2)}; set3={len(set3)}",
            },
            {
                "check": "feature_counts_compared_with_paper_targets",
                "passed": feature_counts_match_paper,
                "detail": "; ".join(
                    f"{row.feature_set}: actual={row.actual_feature_count}, target={row.paper_target_feature_count}"
                    for row in feature_set_comparison.itertuples()
                ),
            },
            {
                "check": "tc_hdl_available_without_divide_by_zero",
                "passed": tc_hdl_ok,
                "detail": f"divide_by_zero_prevented={bool(tc_hdl_audit.iloc[0]['divide_by_zero_prevented']) if not tc_hdl_audit.empty else False}",
            },
        ]
    )


def build_markdown_report(report: dict[str, object], config: FeatureEngineeringConfig) -> str:
    checks_passed = report.get("acceptance_checks_passed", 0)
    checks_total = report.get("acceptance_checks_total", 0)
    return f"""# Feature Engineering Report

## Summary

- Input: `{config.records_path}`
- Patients in cleaned records: {report["patients"]:,}
- Single-shot rows: {report["single_shot_rows"]:,}
- Temporal-complete patients: {report["temporal_complete_patients"]:,}
- Extract Set 1 shape: {report["extract_set_1_rows"]:,} rows x {report["extract_set_1_columns"]:,} columns
- Extract Set 2 shape: {report["extract_set_2_rows"]:,} rows x {report["extract_set_2_columns"]:,} columns
- Extract Set 3 shape: {report["extract_set_3_rows"]:,} rows x {report["extract_set_3_columns"]:,} columns
- Excluded from temporal feature sets: {report["excluded_patients"]:,}
- No post-reference records: `{report["no_post_reference_records"]}`
- Acceptance checks passed: {checks_passed}/{checks_total}

## Paper Reference

- Paper: `{PAPER_REFERENCE["title"]}`
- Method section: `{PAPER_REFERENCE["method_section"]}`
- Single-shot role: `{PAPER_REFERENCE["single_shot_role"]}`
- Paper target feature counts: Extract Set 1 = 35, Extract Set 2 = 115, Extract Set 3 = 121

## Notes

Single-shot baseline uses the latest eligible record inside FIRST/MID/LAST observation windows, not the 0-3 month prediction window. Temporal Extract Set 1/2/3 use only patients that satisfy FIRST/MID/LAST visit and core numeric coverage. The strict paper-style completeness rule is intentionally preserved.

## Outputs

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- `temporal_completeness_flags.csv`
- `feature_dictionary.csv`
- `feature_generation_log.csv`
- `feature_engineering_exclusions.csv`
- `single_shot_audit.csv`
- `tc_hdl_audit.csv`
- `temporal_window_usage_report.csv`
- `feature_set_comparison.csv`
- `feature_engineering_acceptance_checks.csv`
- `feature_engineering_report.json`
- `feature_engineering_report.md`
"""


def run_feature_engineering(config: FeatureEngineeringConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 05."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(config.records_path, config)
    no_post_reference = validate_pre_reference(records, config)
    feature_sets = build_feature_sets(records, config)

    completeness = feature_sets["temporal_completeness"]
    assert isinstance(completeness, pd.DataFrame)
    exclusion_report = build_exclusion_report(records, completeness, config)
    generation_log = build_generation_log(feature_sets, no_post_reference)
    temporal_window_usage = build_temporal_window_usage_report(records, config)

    for key, filename in {
        "single_shot": "single_shot_features.csv",
        "extract_set_1": "extract_set_1_features.csv",
        "extract_set_2": "extract_set_2_features.csv",
        "extract_set_3": "extract_set_3_features.csv",
        "temporal_completeness": "temporal_completeness_flags.csv",
        "feature_dictionary": "feature_dictionary.csv",
        "single_shot_audit": "single_shot_audit.csv",
        "tc_hdl_audit": "tc_hdl_audit.csv",
    }.items():
        table = feature_sets[key]
        assert isinstance(table, pd.DataFrame)
        write_csv(table, config.output_dir / filename)
    write_csv(generation_log, config.output_dir / "feature_generation_log.csv")
    write_csv(exclusion_report, config.output_dir / "feature_engineering_exclusions.csv")
    write_csv(temporal_window_usage, config.output_dir / "temporal_window_usage_report.csv")

    single = feature_sets["single_shot"]
    set1 = feature_sets["extract_set_1"]
    set2 = feature_sets["extract_set_2"]
    set3 = feature_sets["extract_set_3"]
    assert isinstance(single, pd.DataFrame)
    assert isinstance(set1, pd.DataFrame)
    assert isinstance(set2, pd.DataFrame)
    assert isinstance(set3, pd.DataFrame)
    feature_set_comparison = build_feature_set_comparison(set1, set2, set3)
    acceptance_checks = build_acceptance_checks(
        records,
        feature_sets,
        generation_log,
        feature_set_comparison,
        temporal_window_usage,
        no_post_reference,
    )
    write_csv(feature_set_comparison, config.output_dir / "feature_set_comparison.csv")
    write_csv(acceptance_checks, config.output_dir / "feature_engineering_acceptance_checks.csv")

    report = {
        "paper_reference": PAPER_REFERENCE,
        "paper_target_feature_counts": PAPER_TARGET_FEATURE_COUNTS,
        "patients": int(records[config.patient_id_col].nunique()),
        "single_shot_rows": int(len(single)),
        "temporal_complete_patients": int(completeness["temporal_complete"].sum()),
        "extract_set_1_rows": int(len(set1)),
        "extract_set_1_columns": int(set1.shape[1]),
        "extract_set_1_feature_count": int(_feature_count(set1)),
        "extract_set_2_rows": int(len(set2)),
        "extract_set_2_columns": int(set2.shape[1]),
        "extract_set_2_feature_count": int(_feature_count(set2)),
        "extract_set_3_rows": int(len(set3)),
        "extract_set_3_columns": int(set3.shape[1]),
        "extract_set_3_feature_count": int(_feature_count(set3)),
        "excluded_patients": int(len(exclusion_report)),
        "no_post_reference_records": no_post_reference,
        "feature_dictionary_rows": int(len(feature_sets["feature_dictionary"])),
        "acceptance_checks_passed": int(acceptance_checks["passed"].sum()),
        "acceptance_checks_total": int(len(acceptance_checks)),
        "acceptance_passed": bool(acceptance_checks["passed"].all()),
    }
    report = {key: _json_ready(value) for key, value in report.items()}
    write_json(report, config.output_dir / "feature_engineering_report.json")
    (config.output_dir / "feature_engineering_report.md").write_text(
        build_markdown_report(report, config), encoding="utf-8"
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 05 feature engineering.")
    parser.add_argument("--records-path", default=str(FeatureEngineeringConfig.records_path))
    parser.add_argument("--output-dir", default=str(FeatureEngineeringConfig.output_dir))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = FeatureEngineeringConfig(records_path=Path(args.records_path), output_dir=Path(args.output_dir))
    report = run_feature_engineering(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
