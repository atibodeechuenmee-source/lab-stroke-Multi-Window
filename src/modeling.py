"""Stage 06 modeling for temporal stroke-risk prediction.

งานหลัก:
1) โหลด feature tables จาก Stage 05
2) train/evaluate Logistic Regression (class_weight="balanced")
3) ใช้ patient-level CV และบันทึก prediction ต่อ fold
4) รายงาน metrics โดยเน้น G-Mean

ข้อกำกับ:
- baseline single_shot ต้องมีเสมอ
- ตรวจ train/test patient overlap เพื่อกัน leakage
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PAPER_REFERENCE = {
    "title": "Multi-Window Timeframe Temporal Features for Stroke-Risk Prediction",
    "method_section": "Classification Model",
    "algorithm": "LogisticRegression",
    "class_weight": "balanced",
    "paper_cv_strategy": "LOOCV",
    "primary_selection_metric": "G-Mean",
}
TEMPORAL_MODEL_NAMES = ["extract_set_1", "extract_set_2", "extract_set_3"]


@dataclass(frozen=True)
class ModelingConfig:
    feature_dir: Path = Path("output/feature_engineering_output")
    output_dir: Path = Path("output/model_output")
    patient_id_col: str = "patient_id"
    target_col: str = "stroke"
    threshold: float = 0.5
    max_folds: int = 5
    random_state: int = 42


FEATURE_FILES = {
    "single_shot": "single_shot_features.csv",
    "extract_set_1": "extract_set_1_features.csv",
    "extract_set_2": "extract_set_2_features.csv",
    "extract_set_3": "extract_set_3_features.csv",
}


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


def load_feature_tables(config: ModelingConfig) -> dict[str, pd.DataFrame]:
    """โหลด feature tables ที่มีอยู่จริงใน output ของ Stage 05."""
    tables = {}
    for model_name, filename in FEATURE_FILES.items():
        path = config.feature_dir / filename
        if path.exists():
            tables[model_name] = pd.read_csv(path)
    if "single_shot" not in tables:
        raise FileNotFoundError(f"Missing required baseline feature table: {config.feature_dir / FEATURE_FILES['single_shot']}")
    return tables


def numeric_feature_matrix(table: pd.DataFrame, config: ModelingConfig) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """เตรียม X/y โดยใช้เฉพาะคอลัมน์ตัวเลขสำหรับโมเดล."""
    required = [config.patient_id_col, config.target_col]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise KeyError(f"Missing required modeling columns: {missing}")
    table = table.dropna(subset=[config.target_col]).copy()
    patient_ids = table[config.patient_id_col]
    y = pd.to_numeric(table[config.target_col], errors="coerce").astype(int)
    x = table.drop(columns=[config.patient_id_col, config.target_col], errors="ignore")
    x = x.select_dtypes(include=[np.number]).copy()
    return x, y, patient_ids


def choose_cv(y: pd.Series, config: ModelingConfig):
    """เลือก CV strategy ตาม class distribution และขนาดข้อมูล."""
    from sklearn.model_selection import LeaveOneOut, StratifiedKFold

    class_counts = y.value_counts()
    if len(class_counts) < 2:
        return None, "not_run_single_class"
    min_class = int(class_counts.min())
    if min_class < 2:
        return None, "not_run_min_class_lt_2"
    if len(y) <= 200:
        return LeaveOneOut(), "LOOCV"
    folds = min(config.max_folds, min_class)
    return StratifiedKFold(n_splits=folds, shuffle=True, random_state=config.random_state), f"StratifiedKFold_{folds}"


def make_model(config: ModelingConfig):
    """สร้าง pipeline มาตรฐานของ Stage 06."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=config.random_state,
                ),
            ),
        ]
    )


def g_mean(sensitivity: float, specificity: float) -> float:
    return math.sqrt(max(sensitivity, 0.0) * max(specificity, 0.0))


def evaluate_predictions(y_true: list[int], y_pred: list[int], y_prob: list[float]) -> dict[str, float | int]:
    """คำนวณ confusion metrics และ ROC-AUC."""
    from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    roc_auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) == 2 else float("nan")
    pr_auc = average_precision_score(y_true, y_prob) if len(set(y_true)) == 2 else float("nan")
    return {
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "g_mean": float(g_mean(sensitivity, specificity)),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
    }


def train_predict_cv(model_name: str, table: pd.DataFrame, config: ModelingConfig) -> tuple[pd.DataFrame, dict, dict]:
    """เทรนและทำนายแบบ cross-validation สำหรับโมเดลหนึ่งชุด."""
    x, y, patient_ids = numeric_feature_matrix(table, config)
    cv, cv_name = choose_cv(y, config)
    base_config = {
        "model_name": model_name,
        "algorithm": "LogisticRegression",
        "class_weight": "balanced",
        "threshold": config.threshold,
        "cv_strategy": cv_name,
        "n_patients": int(len(y)),
        "n_features": int(x.shape[1]),
        "target_positive_count": int((y == 1).sum()),
        "target_negative_count": int((y == 0).sum()),
        "paper_algorithm_match": True,
        "paper_class_weight_match": True,
        "paper_cv_exact_match": cv_name == PAPER_REFERENCE["paper_cv_strategy"],
    }
    # ถ้าข้อมูลไม่พร้อม (เช่น class เดียว) ให้ skip อย่างโปร่งใส
    if cv is None or x.empty:
        reason = cv_name if cv is None else "not_run_no_numeric_features"
        predictions = pd.DataFrame(
            columns=[config.patient_id_col, "model_name", "fold", "y_true", "y_pred", "y_prob"]
        )
        metrics = {
            **base_config,
            "status": "skipped",
            "skip_reason": reason,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
            "sensitivity": float("nan"),
            "specificity": float("nan"),
            "g_mean": float("nan"),
            "roc_auc": float("nan"),
            "pr_auc": float("nan"),
            "fold_count": 0,
            "patient_overlap_detected": False,
        }
        return predictions, metrics, base_config

    model = make_model(config)
    rows = []
    patient_overlap_detected = False
    for fold_idx, (train_idx, test_idx) in enumerate(cv.split(x, y), start=1):
        # patient-level leakage guard: ห้ามมีคนไข้ซ้ำระหว่าง train/test ใน fold เดียวกัน
        train_ids = set(patient_ids.iloc[train_idx])
        test_ids = set(patient_ids.iloc[test_idx])
        if train_ids & test_ids:
            patient_overlap_detected = True
            raise RuntimeError("Patient leakage detected: train/test patient ids overlap in a fold.")
        model.fit(x.iloc[train_idx], y.iloc[train_idx])
        probs = model.predict_proba(x.iloc[test_idx])[:, 1]
        preds = (probs >= config.threshold).astype(int)
        for pid, true, pred, prob in zip(patient_ids.iloc[test_idx], y.iloc[test_idx], preds, probs):
            rows.append(
                {
                    config.patient_id_col: pid,
                    "model_name": model_name,
                    "fold": fold_idx,
                    "y_true": int(true),
                    "y_pred": int(pred),
                    "y_prob": float(prob),
                }
            )

    predictions = pd.DataFrame(rows)
    eval_metrics = evaluate_predictions(
        predictions["y_true"].astype(int).tolist(),
        predictions["y_pred"].astype(int).tolist(),
        predictions["y_prob"].astype(float).tolist(),
    )
    metrics = {
        **base_config,
        "status": "completed",
        "skip_reason": "",
        "fold_count": int(predictions["fold"].nunique()) if "fold" in predictions.columns else 0,
        "patient_overlap_detected": patient_overlap_detected,
        **eval_metrics,
    }
    return predictions, metrics, base_config


def build_skipped_model_report(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """แยกรายงาน model ที่ถูก skip พร้อมเหตุผล เพื่อให้ validation อ่านต่อได้ง่าย."""
    if metrics_df.empty or "status" not in metrics_df.columns:
        return pd.DataFrame(columns=["model_name", "skip_reason", "n_patients", "target_positive_count"])
    skipped = metrics_df[metrics_df["status"] == "skipped"].copy()
    if skipped.empty:
        return pd.DataFrame(columns=["model_name", "skip_reason", "n_patients", "target_positive_count"])
    return skipped[
        [
            "model_name",
            "skip_reason",
            "n_patients",
            "n_features",
            "target_positive_count",
            "target_negative_count",
            "cv_strategy",
        ]
    ].copy()


def build_cv_policy_report(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """สรุปว่าแต่ละ model ใช้ LOOCV ตาม paper หรือ fallback CV เพราะเหตุใด."""
    if metrics_df.empty:
        return pd.DataFrame()
    rows = []
    for row in metrics_df.to_dict(orient="records"):
        cv_strategy = str(row.get("cv_strategy", ""))
        rows.append(
            {
                "model_name": row.get("model_name", ""),
                "paper_cv_strategy": PAPER_REFERENCE["paper_cv_strategy"],
                "actual_cv_strategy": cv_strategy,
                "paper_cv_exact_match": bool(cv_strategy == PAPER_REFERENCE["paper_cv_strategy"]),
                "fallback_reason": ""
                if cv_strategy == PAPER_REFERENCE["paper_cv_strategy"]
                else "large baseline table uses stratified patient-level CV; insufficient temporal class count may skip",
                "n_patients": row.get("n_patients", 0),
                "target_positive_count": row.get("target_positive_count", 0),
                "target_negative_count": row.get("target_negative_count", 0),
            }
        )
    return pd.DataFrame(rows)


def build_acceptance_checks(
    tables: dict[str, pd.DataFrame],
    metrics_df: pd.DataFrame,
    all_predictions: pd.DataFrame,
    skipped_report: pd.DataFrame,
) -> pd.DataFrame:
    """สร้าง acceptance checks ตาม docs/pipeline/06-modeling.md."""
    baseline_seen = "single_shot" in tables
    baseline_attempted = bool(
        not metrics_df.empty and (metrics_df["model_name"] == "single_shot").any()
    )
    temporal_seen = [name for name in TEMPORAL_MODEL_NAMES if name in tables]
    temporal_metrics = metrics_df[metrics_df["model_name"].isin(temporal_seen)] if not metrics_df.empty else pd.DataFrame()
    skipped_temporal = temporal_metrics[temporal_metrics["status"] == "skipped"] if not temporal_metrics.empty else pd.DataFrame()
    skipped_report_ok = len(skipped_temporal) == 0 or not skipped_report.empty
    patient_overlap_ok = (
        bool((metrics_df["patient_overlap_detected"] == False).all())  # noqa: E712
        if "patient_overlap_detected" in metrics_df.columns
        else False
    )
    required_metrics = {"sensitivity", "specificity", "g_mean", "roc_auc", "pr_auc"}
    metrics_reported = required_metrics.issubset(set(metrics_df.columns))
    completed = metrics_df[metrics_df["status"] == "completed"] if "status" in metrics_df.columns else pd.DataFrame()
    best_by_gmean = True
    if not completed.empty:
        reported_best = metrics_df.iloc[0]["model_name"]
        actual_best = completed.sort_values("g_mean", ascending=False, na_position="last").iloc[0]["model_name"]
        best_by_gmean = bool(reported_best == actual_best)
    predictions_available = not all_predictions.empty and {"model_name", "y_true", "y_pred", "y_prob"}.issubset(
        all_predictions.columns
    )
    return pd.DataFrame(
        [
            {
                "check": "single_shot_baseline_attempted",
                "passed": baseline_seen and baseline_attempted,
                "detail": "single-shot baseline is required comparator",
            },
            {
                "check": "skipped_temporal_models_reported_with_reason",
                "passed": skipped_report_ok,
                "detail": f"skipped_temporal_models={len(skipped_temporal)}",
            },
            {
                "check": "train_test_patient_overlap_prevented",
                "passed": patient_overlap_ok,
                "detail": "patient ids are checked per fold",
            },
            {
                "check": "required_metrics_reported",
                "passed": metrics_reported,
                "detail": ", ".join(sorted(required_metrics)),
            },
            {
                "check": "best_model_selected_by_g_mean",
                "passed": best_by_gmean,
                "detail": "metrics table sorted by G-Mean with NaN last",
            },
            {
                "check": "prediction_files_available_for_validation",
                "passed": predictions_available,
                "detail": "out-of-fold predictions retained for Stage 08 McNemar testing",
            },
            {
                "check": "logistic_regression_balanced_used",
                "passed": bool(
                    (metrics_df["algorithm"] == PAPER_REFERENCE["algorithm"]).all()
                    and (metrics_df["class_weight"] == PAPER_REFERENCE["class_weight"]).all()
                )
                if not metrics_df.empty
                else False,
                "detail": "LogisticRegression(class_weight='balanced')",
            },
        ]
    )


def run_modeling(config: ModelingConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 06."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    tables = load_feature_tables(config)
    all_predictions = []
    metrics_rows = []
    model_configs = []

    for model_name, table in tables.items():
        predictions, metrics, model_config = train_predict_cv(model_name, table, config)
        metrics_rows.append(metrics)
        model_configs.append(model_config)
        if not predictions.empty:
            all_predictions.append(predictions)
            write_csv(predictions, config.output_dir / f"{model_name}_predictions.csv")

    metrics_df = pd.DataFrame(metrics_rows)
    # จัดอันดับโมเดลด้วย G-Mean เพื่อสะท้อนสมดุล sensitivity/specificity
    if "g_mean" in metrics_df.columns:
        metrics_df = metrics_df.sort_values("g_mean", ascending=False, na_position="last")
    write_csv(metrics_df, config.output_dir / "model_cv_metrics.csv")
    write_csv(pd.DataFrame(model_configs), config.output_dir / "model_config_log.csv")
    if all_predictions:
        all_predictions_df = pd.concat(all_predictions, ignore_index=True)
        write_csv(all_predictions_df, config.output_dir / "all_model_predictions.csv")
    else:
        all_predictions_df = pd.DataFrame()

    skipped_report = build_skipped_model_report(metrics_df)
    cv_policy_report = build_cv_policy_report(metrics_df)
    acceptance_checks = build_acceptance_checks(tables, metrics_df, all_predictions_df, skipped_report)
    write_csv(skipped_report, config.output_dir / "skipped_models_report.csv")
    write_csv(cv_policy_report, config.output_dir / "cv_policy_report.csv")
    write_csv(acceptance_checks, config.output_dir / "modeling_acceptance_checks.csv")

    summary = {
        "paper_reference": PAPER_REFERENCE,
        "feature_dir": str(config.feature_dir),
        "output_dir": str(config.output_dir),
        "models_seen": list(tables.keys()),
        "models_completed": int((metrics_df["status"] == "completed").sum()) if "status" in metrics_df else 0,
        "models_skipped": int((metrics_df["status"] == "skipped").sum()) if "status" in metrics_df else 0,
        "best_model": str(metrics_df.iloc[0]["model_name"]) if not metrics_df.empty else "",
        "best_g_mean": float(metrics_df.iloc[0]["g_mean"]) if not metrics_df.empty and pd.notna(metrics_df.iloc[0]["g_mean"]) else None,
        "acceptance_checks_passed": int(acceptance_checks["passed"].sum()),
        "acceptance_checks_total": int(len(acceptance_checks)),
        "acceptance_passed": bool(acceptance_checks["passed"].all()),
    }
    summary = {key: _json_ready(value) for key, value in summary.items()}
    write_json(summary, config.output_dir / "modeling_report.json")
    (config.output_dir / "modeling_report.md").write_text(build_report_markdown(summary, metrics_df), encoding="utf-8")
    return summary


def build_report_markdown(summary: dict[str, object], metrics: pd.DataFrame) -> str:
    completed = metrics[metrics["status"] == "completed"] if "status" in metrics else pd.DataFrame()
    skipped = metrics[metrics["status"] == "skipped"] if "status" in metrics else pd.DataFrame()
    best_line = "No completed model."
    if not completed.empty:
        best = completed.sort_values("g_mean", ascending=False).iloc[0]
        best_line = f"Best completed model: `{best['model_name']}` with G-Mean `{best['g_mean']:.4f}`."
    skipped_lines = "\n".join(
        f"- `{row['model_name']}` skipped: {row['skip_reason']}" for _, row in skipped.iterrows()
    )
    if not skipped_lines:
        skipped_lines = "- None"
    checks_passed = summary.get("acceptance_checks_passed", 0)
    checks_total = summary.get("acceptance_checks_total", 0)
    return f"""# Modeling Report

## Summary

- Feature input directory: `{summary["feature_dir"]}`
- Output directory: `{summary["output_dir"]}`
- Models seen: {", ".join(summary["models_seen"])}
- Models completed: {summary["models_completed"]}
- Models skipped: {summary["models_skipped"]}
- {best_line}
- Acceptance checks passed: {checks_passed}/{checks_total}

## Paper Reference

- Paper: `{PAPER_REFERENCE["title"]}`
- Method section: `{PAPER_REFERENCE["method_section"]}`
- Algorithm: `{PAPER_REFERENCE["algorithm"]}`
- Class weight: `{PAPER_REFERENCE["class_weight"]}`
- Paper CV strategy: `{PAPER_REFERENCE["paper_cv_strategy"]}`
- Primary selection metric: `{PAPER_REFERENCE["primary_selection_metric"]}`

## Notes

Logistic Regression uses `class_weight="balanced"` and patient-level cross-validation. LOOCV is used automatically for small feature tables; larger tables use stratified patient-level CV for computational practicality.

## Skipped Models

{skipped_lines}

## Outputs

- `model_cv_metrics.csv`
- `model_config_log.csv`
- `all_model_predictions.csv`
- `<model_name>_predictions.csv`
- `skipped_models_report.csv`
- `cv_policy_report.csv`
- `modeling_acceptance_checks.csv`
- `modeling_report.json`
- `modeling_report.md`
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 06 modeling.")
    parser.add_argument("--feature-dir", default=str(ModelingConfig.feature_dir))
    parser.add_argument("--output-dir", default=str(ModelingConfig.output_dir))
    parser.add_argument("--max-folds", type=int, default=ModelingConfig.max_folds)
    parser.add_argument("--threshold", type=float, default=ModelingConfig.threshold)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ModelingConfig(
        feature_dir=Path(args.feature_dir),
        output_dir=Path(args.output_dir),
        max_folds=args.max_folds,
        threshold=args.threshold,
    )
    report = run_modeling(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
