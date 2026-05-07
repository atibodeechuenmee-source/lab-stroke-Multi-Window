"""Stage 05 feature engineering for temporal stroke-risk prediction.

Implements docs/pipeline/05-feature-engineering.md. The stage creates a
single-shot baseline and temporal Extract Set 1/2/3 feature tables from
cleaned pre-reference records only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


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


def ensure_tc_hdl_ratio(records: pd.DataFrame) -> pd.DataFrame:
    prepared = records.copy()
    if "tc_hdl_ratio" not in prepared.columns and {"cholesterol", "hdl"}.issubset(prepared.columns):
        prepared["tc_hdl_ratio"] = np.where(
            pd.to_numeric(prepared["hdl"], errors="coerce") > 0,
            pd.to_numeric(prepared["cholesterol"], errors="coerce") / pd.to_numeric(prepared["hdl"], errors="coerce"),
            np.nan,
        )
    return prepared


def latest_non_null(series: pd.Series):
    values = series.dropna()
    return values.iloc[-1] if len(values) else np.nan


def validate_pre_reference(records: pd.DataFrame, config: FeatureEngineeringConfig) -> bool:
    if config.reference_date_col not in records.columns:
        return True
    valid = records[[config.visit_date_col, config.reference_date_col]].dropna()
    return bool((valid[config.visit_date_col] <= valid[config.reference_date_col]).all())


def build_single_shot(records: pd.DataFrame, config: FeatureEngineeringConfig) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    sorted_records = records.sort_values([config.patient_id_col, config.visit_date_col])
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
            "source_window": "latest_pre_reference",
            "aggregation": "latest record",
            "feature_set": "single_shot",
        }
        for old_name, new_name in rename.items()
    ]
    return result, dictionary


def temporal_complete_patient_ids(records: pd.DataFrame, config: FeatureEngineeringConfig) -> tuple[set, pd.DataFrame]:
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
                "source_window": "latest_pre_reference",
                "aggregation": "latest non-null",
                "feature_set": feature_set,
            }
        )
    return result, dictionary


def add_statistical_descriptors(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    result = table.copy()
    dictionary = []
    aggregations = {
        "min": "min",
        "max": "max",
        "std": lambda x: x.std(ddof=0),
        "first": "first",
        "last": "last",
        "count": "count",
    }
    for window in WINDOWS:
        wg = records[records["window"] == window].sort_values(["patient_id", "visit_date"])
        for name, col in NUMERIC_COLUMNS.items():
            if col not in wg.columns:
                continue
            grouped = wg.groupby("patient_id")[col]
            for suffix, agg in aggregations.items():
                feature = f"{window.lower()}_{name}_{suffix}"
                values = grouped.agg(agg).rename(feature)
                result = result.join(values, how="left")
                dictionary.append(
                    {
                        "feature": feature,
                        "source_column": col,
                        "source_window": window,
                        "aggregation": suffix,
                        "feature_set": "extract_set_2",
                    }
                )
    return result, dictionary


def add_temporal_descriptors(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    result = table.copy()
    dictionary = []
    first_records = records[records["window"] == "FIRST"]
    last_records = records[records["window"] == "LAST"]
    for name, col in NUMERIC_COLUMNS.items():
        if col not in records.columns:
            continue
        first_mean = first_records.groupby("patient_id")[col].mean()
        last_mean = last_records.groupby("patient_id")[col].mean()
        delta = (last_mean - first_mean).rename(f"{name}_delta_last_first")
        slope = (delta / (WINDOW_MONTH_CENTERS["FIRST"] - WINDOW_MONTH_CENTERS["LAST"])).rename(
            f"{name}_slope_last_first"
        )
        result = result.join(delta, how="left")
        result = result.join(slope, how="left")
        for feature, agg in [(delta.name, "LAST mean - FIRST mean"), (slope.name, "delta / 6 months")]:
            dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": "FIRST,LAST",
                    "aggregation": agg,
                    "feature_set": "extract_set_2",
                }
            )

        first_min = first_records.groupby("patient_id")[col].min()
        last_min = last_records.groupby("patient_id")[col].min()
        first_max = first_records.groupby("patient_id")[col].max()
        last_max = last_records.groupby("patient_id")[col].max()
        first_count = first_records.groupby("patient_id")[col].count()
        last_count = last_records.groupby("patient_id")[col].count()
        extra = {
            f"{name}_min_diff_last_first": last_min - first_min,
            f"{name}_max_diff_last_first": last_max - first_max,
            f"{name}_count_diff_last_first": last_count - first_count,
        }
        for feature, values in extra.items():
            result = result.join(values.rename(feature), how="left")
            dictionary.append(
                {
                    "feature": feature,
                    "source_column": col,
                    "source_window": "FIRST,LAST",
                    "aggregation": feature.replace(f"{name}_", ""),
                    "feature_set": "extract_set_2",
                }
            )
    return result, dictionary


def add_risk_factors(table: pd.DataFrame, records: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
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
                "source_window": "latest_pre_reference",
                "aggregation": "latest non-null",
                "feature_set": "extract_set_3",
            }
        )
    return result, dictionary


def build_feature_sets(records: pd.DataFrame, config: FeatureEngineeringConfig) -> dict[str, pd.DataFrame | list[dict[str, str]]]:
    records = ensure_tc_hdl_ratio(records)
    complete_ids, completeness = temporal_complete_patient_ids(records, config)
    temporal_records = records[records[config.patient_id_col].isin(complete_ids) & records["window"].isin(WINDOWS)].copy()

    single_shot, single_dict = build_single_shot(records, config)

    set1_base = base_patient_table(records, complete_ids, config)
    set1_table, set1_dict = add_window_means(set1_base, temporal_records)
    set1_table, set1_cat_dict = add_latest_categorical(set1_table, temporal_records, "extract_set_1")
    set1 = set1_table.reset_index()

    set2_table, stat_dict = add_statistical_descriptors(set1_table, temporal_records)
    set2_table, temporal_dict = add_temporal_descriptors(set2_table, temporal_records)
    set2 = set2_table.reset_index()

    set3_table, risk_dict = add_risk_factors(set2_table, temporal_records)
    set3 = set3_table.reset_index()

    dictionary = single_dict + set1_dict + set1_cat_dict + stat_dict + temporal_dict + risk_dict
    return {
        "single_shot": single_shot,
        "extract_set_1": set1,
        "extract_set_2": set2,
        "extract_set_3": set3,
        "temporal_completeness": completeness,
        "feature_dictionary": pd.DataFrame(dictionary),
    }


def build_exclusion_report(records: pd.DataFrame, completeness: pd.DataFrame, config: FeatureEngineeringConfig) -> pd.DataFrame:
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


def build_markdown_report(report: dict[str, object], config: FeatureEngineeringConfig) -> str:
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

## Notes

Single-shot baseline uses the latest pre-reference record for every patient. Temporal Extract Set 1/2/3 use only patients that satisfy FIRST/MID/LAST visit and core numeric coverage. The strict paper-style completeness rule is intentionally preserved.

## Outputs

- `single_shot_features.csv`
- `extract_set_1_features.csv`
- `extract_set_2_features.csv`
- `extract_set_3_features.csv`
- `temporal_completeness_flags.csv`
- `feature_dictionary.csv`
- `feature_generation_log.csv`
- `feature_engineering_exclusions.csv`
- `feature_engineering_report.json`
- `feature_engineering_report.md`
"""


def run_feature_engineering(config: FeatureEngineeringConfig) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(config.records_path, config)
    no_post_reference = validate_pre_reference(records, config)
    feature_sets = build_feature_sets(records, config)

    completeness = feature_sets["temporal_completeness"]
    assert isinstance(completeness, pd.DataFrame)
    exclusion_report = build_exclusion_report(records, completeness, config)
    generation_log = build_generation_log(feature_sets, no_post_reference)

    for key, filename in {
        "single_shot": "single_shot_features.csv",
        "extract_set_1": "extract_set_1_features.csv",
        "extract_set_2": "extract_set_2_features.csv",
        "extract_set_3": "extract_set_3_features.csv",
        "temporal_completeness": "temporal_completeness_flags.csv",
        "feature_dictionary": "feature_dictionary.csv",
    }.items():
        table = feature_sets[key]
        assert isinstance(table, pd.DataFrame)
        write_csv(table, config.output_dir / filename)
    write_csv(generation_log, config.output_dir / "feature_generation_log.csv")
    write_csv(exclusion_report, config.output_dir / "feature_engineering_exclusions.csv")

    single = feature_sets["single_shot"]
    set1 = feature_sets["extract_set_1"]
    set2 = feature_sets["extract_set_2"]
    set3 = feature_sets["extract_set_3"]
    assert isinstance(single, pd.DataFrame)
    assert isinstance(set1, pd.DataFrame)
    assert isinstance(set2, pd.DataFrame)
    assert isinstance(set3, pd.DataFrame)
    report = {
        "patients": int(records[config.patient_id_col].nunique()),
        "single_shot_rows": int(len(single)),
        "temporal_complete_patients": int(completeness["temporal_complete"].sum()),
        "extract_set_1_rows": int(len(set1)),
        "extract_set_1_columns": int(set1.shape[1]),
        "extract_set_2_rows": int(len(set2)),
        "extract_set_2_columns": int(set2.shape[1]),
        "extract_set_3_rows": int(len(set3)),
        "extract_set_3_columns": int(set3.shape[1]),
        "excluded_patients": int(len(exclusion_report)),
        "no_post_reference_records": no_post_reference,
    }
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

