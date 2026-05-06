"""Multi-window temporal stroke-risk prediction pipeline.

This module implements the code blueprint described in
docs/pipeline/00-pipeline-overview.md.  It is intentionally conservative:
all modeling features are built from pre-reference records only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


STROKE_PATTERN = re.compile(r"\bI6[0-8](?:\.\d+)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class PipelineConfig:
    raw_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    output_dir: Path = Path("output/pipeline_runs/temporal_pipeline")
    patient_id_col: str = "hn"
    visit_date_col: str = "vstdate"
    principal_dx_col: str = "PrincipleDiagnosis"
    comorbidity_dx_col: str = "ComorbidityDiagnosis"
    months_per_day: float = 30.4375


NUMERIC_COLUMNS = {
    "bps": "bps",
    "bpd": "bpd",
    "hdl": "HDL",
    "ldl": "LDL",
    "fbs": "FBS",
    "bmi": "bmi",
    "egfr": "eGFR",
    "creatinine": "Creatinine",
    "cholesterol": "Cholesterol",
    "triglyceride": "Triglyceride",
}

CATEGORICAL_COLUMNS = {
    "sex": "sex",
    "af": "AF",
    "smoke": "smoke",
    "drinking": "drinking",
}

RISK_FACTOR_COLUMNS = {
    "heart_disease": "heart_disease",
    "hypertension": "hypertension",
    "diabetes": "diabetes",
    "statin": "Statin",
    "antihypertensive": "Antihypertensive_flag",
}

WINDOWS = {
    "FIRST": (21.0, 9.0),
    "MID": (18.0, 6.0),
    "LAST": (15.0, 3.0),
}


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load a raw EHR table from Excel or CSV."""
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported raw file type: {path}")


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif path.suffix.lower() == ".json":
        path.write_text(df.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output table type: {path}")


def audit_raw_data(df: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    """Create raw schema, missingness, and record coverage summaries."""
    output_dir.mkdir(parents=True, exist_ok=True)
    schema = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(df[col].dtype) for col in df.columns],
            "missing_count": [int(df[col].isna().sum()) for col in df.columns],
            "missing_percent": [float(df[col].isna().mean()) for col in df.columns],
            "example_values": [
                ", ".join(map(str, df[col].dropna().astype(str).head(3).tolist())) for col in df.columns
            ],
        }
    )
    write_table(schema, output_dir / "raw_schema_summary.csv")

    summary = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": list(map(str, df.columns)),
    }
    (output_dir / "raw_data_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def clean_records(df: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Standardize dates, numeric fields, binary flags, and implausible values."""
    required = [config.patient_id_col, config.visit_date_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    cleaned = df.copy()
    cleaned[config.visit_date_col] = pd.to_datetime(cleaned[config.visit_date_col], errors="coerce")
    cleaned = cleaned.dropna(subset=[config.patient_id_col, config.visit_date_col])
    cleaned = cleaned.drop_duplicates()

    for col in NUMERIC_COLUMNS.values():
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    plausible_ranges = {
        "bps": (40, 260),
        "bpd": (20, 160),
        "HDL": (1, 200),
        "LDL": (1, 400),
        "FBS": (20, 600),
        "bmi": (5, 80),
        "eGFR": (1, 200),
        "Creatinine": (0.1, 30),
        "Cholesterol": (20, 600),
        "Triglyceride": (1, 2000),
    }
    for col, (low, high) in plausible_ranges.items():
        if col in cleaned.columns:
            cleaned.loc[~cleaned[col].between(low, high), col] = np.nan

    for col in [*CATEGORICAL_COLUMNS.values(), *RISK_FACTOR_COLUMNS.values()]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            cleaned.loc[~cleaned[col].isin([0, 1]), col] = np.nan

    if "TC:HDL_ratio" not in cleaned.columns and {"Cholesterol", "HDL"}.issubset(cleaned.columns):
        cleaned["TC:HDL_ratio"] = np.where(cleaned["HDL"] > 0, cleaned["Cholesterol"] / cleaned["HDL"], np.nan)

    return cleaned


def _stroke_mask(df: pd.DataFrame, diagnosis_cols: Iterable[str]) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for col in diagnosis_cols:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.contains(STROKE_PATTERN, na=False)
    return mask


def build_target_and_cohort(df: pd.DataFrame, config: PipelineConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build patient labels, reference dates, pre-reference records, and windows."""
    diagnosis_cols = [config.principal_dx_col, config.comorbidity_dx_col]
    working = df.copy()
    working["is_stroke_event"] = _stroke_mask(working, diagnosis_cols)

    stroke_dates = (
        working.loc[working["is_stroke_event"]]
        .groupby(config.patient_id_col)[config.visit_date_col]
        .min()
        .rename("first_stroke_date")
    )
    last_visits = working.groupby(config.patient_id_col)[config.visit_date_col].max().rename("last_visit_date")
    cohort = last_visits.to_frame().join(stroke_dates, how="left")
    cohort["stroke"] = cohort["first_stroke_date"].notna().astype(int)
    cohort["reference_date"] = cohort["first_stroke_date"].fillna(cohort["last_visit_date"])
    cohort = cohort.reset_index()

    pre_reference = working.merge(
        cohort[[config.patient_id_col, "stroke", "reference_date"]],
        on=config.patient_id_col,
        how="inner",
    )
    pre_reference = pre_reference[pre_reference[config.visit_date_col] <= pre_reference["reference_date"]].copy()
    pre_reference["months_before_reference"] = (
        pre_reference["reference_date"] - pre_reference[config.visit_date_col]
    ).dt.days / config.months_per_day
    pre_reference["window"] = assign_windows(pre_reference["months_before_reference"])

    return cohort, pre_reference


def assign_windows(months_before_reference: pd.Series) -> pd.Series:
    labels = pd.Series(pd.NA, index=months_before_reference.index, dtype="object")
    for name, (upper, lower) in WINDOWS.items():
        labels.loc[months_before_reference.between(lower, upper, inclusive="both")] = name
    return labels


def temporal_completeness(pre_reference: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Flag patients with visits and complete core numeric variables in every window."""
    rows: list[dict[str, object]] = []
    grouped = pre_reference.dropna(subset=["window"]).groupby(config.patient_id_col)
    for patient_id, group in grouped:
        row: dict[str, object] = {config.patient_id_col: patient_id}
        complete = True
        for window in WINDOWS:
            wg = group[group["window"] == window]
            row[f"{window.lower()}_visit_count"] = int(len(wg))
            has_visit = len(wg) > 0
            has_core = all(col in wg.columns and wg[col].notna().any() for col in NUMERIC_COLUMNS.values())
            row[f"{window.lower()}_has_visit"] = has_visit
            row[f"{window.lower()}_has_core_numeric"] = has_core
            complete = complete and has_visit and has_core
        row["temporal_complete"] = complete
        rows.append(row)
    return pd.DataFrame(rows)


def _latest_non_null(series: pd.Series):
    values = series.dropna()
    return values.iloc[-1] if len(values) else np.nan


def build_single_shot_features(pre_reference: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Build latest pre-reference record features."""
    cols = [
        config.patient_id_col,
        config.visit_date_col,
        *NUMERIC_COLUMNS.values(),
        *CATEGORICAL_COLUMNS.values(),
        *RISK_FACTOR_COLUMNS.values(),
        "TC:HDL_ratio",
    ]
    existing = [col for col in cols if col in pre_reference.columns]
    latest = (
        pre_reference.sort_values([config.patient_id_col, config.visit_date_col])
        .groupby(config.patient_id_col)
        .tail(1)[existing]
        .copy()
    )
    latest = latest.rename(columns={col: f"baseline_{col}" for col in latest.columns if col != config.patient_id_col})
    return latest


def build_temporal_features(
    pre_reference: pd.DataFrame, cohort: pd.DataFrame, config: PipelineConfig
) -> dict[str, pd.DataFrame]:
    """Build Extract Set 1/2/3 feature tables."""
    complete = temporal_completeness(pre_reference, config)
    complete_ids = complete.loc[complete["temporal_complete"], config.patient_id_col]
    temporal = pre_reference[pre_reference[config.patient_id_col].isin(complete_ids)].dropna(subset=["window"]).copy()

    patient_index = cohort[cohort[config.patient_id_col].isin(complete_ids)][[config.patient_id_col, "stroke"]].copy()
    feature_table = patient_index.set_index(config.patient_id_col)

    for window in WINDOWS:
        wg = temporal[temporal["window"] == window].sort_values([config.patient_id_col, config.visit_date_col])
        agg_map = {col: ["mean"] for col in NUMERIC_COLUMNS.values() if col in wg.columns}
        if agg_map:
            means = wg.groupby(config.patient_id_col).agg(agg_map)
            means.columns = [f"{window.lower()}_{col}_{stat}" for col, stat in means.columns]
            feature_table = feature_table.join(means, how="left")

    set1 = feature_table.reset_index()

    set2 = feature_table.copy()
    for window in WINDOWS:
        wg = temporal[temporal["window"] == window].sort_values([config.patient_id_col, config.visit_date_col])
        for feature_name, col in NUMERIC_COLUMNS.items():
            if col not in wg.columns:
                continue
            grouped = wg.groupby(config.patient_id_col)[col]
            stats = pd.DataFrame(
                {
                    f"{window.lower()}_{feature_name}_min": grouped.min(),
                    f"{window.lower()}_{feature_name}_max": grouped.max(),
                    f"{window.lower()}_{feature_name}_std": grouped.std(ddof=0),
                    f"{window.lower()}_{feature_name}_first": grouped.first(),
                    f"{window.lower()}_{feature_name}_last": grouped.last(),
                    f"{window.lower()}_{feature_name}_count": grouped.count(),
                }
            )
            set2 = set2.join(stats, how="left")

    for feature_name, col in NUMERIC_COLUMNS.items():
        first = temporal[temporal["window"] == "FIRST"].groupby(config.patient_id_col)[col].mean()
        last = temporal[temporal["window"] == "LAST"].groupby(config.patient_id_col)[col].mean()
        delta = last - first
        set2[f"{feature_name}_delta_last_first"] = delta
        set2[f"{feature_name}_slope_last_first"] = delta / 12.0

    set2 = set2.reset_index()

    set3 = set2.set_index(config.patient_id_col)
    latest = pre_reference.sort_values([config.patient_id_col, config.visit_date_col]).groupby(config.patient_id_col)
    for name, col in {**CATEGORICAL_COLUMNS, **RISK_FACTOR_COLUMNS, "tc_hdl_ratio": "TC:HDL_ratio"}.items():
        if col in pre_reference.columns:
            set3[f"latest_{name}"] = latest[col].agg(_latest_non_null)
    set3 = set3.reset_index()

    return {
        "temporal_completeness": complete,
        "single_shot": build_single_shot_features(pre_reference, config),
        "extract_set_1": set1,
        "extract_set_2": set2,
        "extract_set_3": set3,
    }


def _gmean(sensitivity: float, specificity: float) -> float:
    return math.sqrt(max(sensitivity, 0.0) * max(specificity, 0.0))


def train_and_validate(feature_tables: dict[str, pd.DataFrame], output_dir: Path, config: PipelineConfig) -> pd.DataFrame:
    """Train Logistic Regression models with patient-level stratified CV."""
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import confusion_matrix, roc_auc_score
        from sklearn.model_selection import StratifiedKFold
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for modeling. Install scikit-learn or skip modeling.") from exc

    results = []
    predictions = {}
    for name in ["single_shot", "extract_set_1", "extract_set_2", "extract_set_3"]:
        table = feature_tables[name].copy()
        if "stroke" not in table.columns:
            table = table.merge(
                feature_tables["extract_set_3"][[config.patient_id_col, "stroke"]],
                on=config.patient_id_col,
                how="inner",
            )
        table = table.dropna(subset=["stroke"])
        if table["stroke"].nunique() < 2:
            continue

        y = table["stroke"].astype(int)
        x = table.drop(columns=[config.patient_id_col, "stroke"], errors="ignore")
        x = x.select_dtypes(include=[np.number])
        if x.empty:
            continue

        min_class = int(y.value_counts().min())
        folds = max(2, min(5, min_class))
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        y_true = []
        y_pred = []
        y_prob = []

        model = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)),
            ]
        )
        for train_idx, test_idx in cv.split(x, y):
            model.fit(x.iloc[train_idx], y.iloc[train_idx])
            probs = model.predict_proba(x.iloc[test_idx])[:, 1]
            preds = (probs >= 0.5).astype(int)
            y_true.extend(y.iloc[test_idx].tolist())
            y_pred.extend(preds.tolist())
            y_prob.extend(probs.tolist())

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) == 2 else np.nan
        results.append(
            {
                "model": name,
                "n_patients": int(len(y_true)),
                "n_features": int(x.shape[1]),
                "sensitivity": sensitivity,
                "specificity": specificity,
                "g_mean": _gmean(sensitivity, specificity),
                "roc_auc": auc,
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
            }
        )
        predictions[name] = pd.DataFrame({"y_true": y_true, "y_pred": y_pred, "y_prob": y_prob})

    metrics = pd.DataFrame(results).sort_values("g_mean", ascending=False)
    write_table(metrics, output_dir / "validation_metrics.csv")

    if {"single_shot", "extract_set_3"}.issubset(predictions):
        mcnemar = mcnemar_test(predictions["single_shot"], predictions["extract_set_3"])
        (output_dir / "mcnemar_single_shot_vs_extract_set_3.json").write_text(
            json.dumps(mcnemar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return metrics


def mcnemar_test(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, float]:
    """Compute McNemar's test with continuity correction for paired predictions."""
    n = min(len(left), len(right))
    l_ok = left.iloc[:n]["y_true"].to_numpy() == left.iloc[:n]["y_pred"].to_numpy()
    r_ok = right.iloc[:n]["y_true"].to_numpy() == right.iloc[:n]["y_pred"].to_numpy()
    b = int(np.sum(l_ok & ~r_ok))
    c = int(np.sum(~l_ok & r_ok))
    statistic = ((abs(b - c) - 1) ** 2 / (b + c)) if (b + c) else 0.0
    try:
        from scipy.stats import chi2

        p_value = float(1 - chi2.cdf(statistic, df=1))
    except ImportError:
        p_value = float("nan")
    return {"left_correct_right_wrong": b, "left_wrong_right_correct": c, "chi_square": statistic, "p_value": p_value}


def run_pipeline(config: PipelineConfig, skip_modeling: bool = False) -> None:
    raw_output = config.output_dir / "raw_data_output"
    cohort_output = config.output_dir / "target_cohort_output"
    cleaning_output = config.output_dir / "data_cleaning_output"
    feature_output = config.output_dir / "feature_engineering_output"
    validation_output = config.output_dir / "validation_output"
    for path in [raw_output, cohort_output, cleaning_output, feature_output, validation_output]:
        path.mkdir(parents=True, exist_ok=True)

    raw = load_raw_data(config.raw_path)
    audit_raw_data(raw, raw_output)

    cleaned = clean_records(raw, config)
    write_table(cleaned, cleaning_output / "cleaned_pre_cohort_records.csv")

    cohort, pre_reference = build_target_and_cohort(cleaned, config)
    write_table(cohort, cohort_output / "patient_level_cohort.csv")
    write_table(pre_reference, cohort_output / "pre_reference_records_with_windows.csv")

    features = build_temporal_features(pre_reference, cohort, config)
    for name, table in features.items():
        write_table(table, feature_output / f"{name}.csv")

    manifest = {
        "raw_path": str(config.raw_path),
        "output_dir": str(config.output_dir),
        "raw_rows": int(len(raw)),
        "cleaned_rows": int(len(cleaned)),
        "patients": int(len(cohort)),
        "pre_reference_rows": int(len(pre_reference)),
        "temporal_complete_patients": int(features["temporal_completeness"]["temporal_complete"].sum()),
        "skip_modeling": skip_modeling,
    }
    if not skip_modeling:
        metrics = train_and_validate(features, validation_output, config)
        manifest["model_count"] = int(len(metrics))
    (config.output_dir / "pipeline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-window temporal stroke-risk pipeline.")
    parser.add_argument("--raw-path", default=str(PipelineConfig.raw_path), help="Path to raw EHR Excel/CSV file.")
    parser.add_argument("--output-dir", default=str(PipelineConfig.output_dir), help="Directory for pipeline outputs.")
    parser.add_argument("--skip-modeling", action="store_true", help="Generate audit/cohort/features without modeling.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(raw_path=Path(args.raw_path), output_dir=Path(args.output_dir))
    run_pipeline(config, skip_modeling=args.skip_modeling)


if __name__ == "__main__":
    main()

