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

import numpy as np
import pandas as pd


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
    from sklearn.metrics import confusion_matrix, roc_auc_score

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    roc_auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) == 2 else float("nan")
    return {
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "g_mean": float(g_mean(sensitivity, specificity)),
        "roc_auc": float(roc_auc),
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
        }
        return predictions, metrics, base_config

    model = make_model(config)
    rows = []
    for fold_idx, (train_idx, test_idx) in enumerate(cv.split(x, y), start=1):
        # patient-level leakage guard: ห้ามมีคนไข้ซ้ำระหว่าง train/test ใน fold เดียวกัน
        train_ids = set(patient_ids.iloc[train_idx])
        test_ids = set(patient_ids.iloc[test_idx])
        if train_ids & test_ids:
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
    metrics = {**base_config, "status": "completed", "skip_reason": "", **eval_metrics}
    return predictions, metrics, base_config


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
        write_csv(pd.concat(all_predictions, ignore_index=True), config.output_dir / "all_model_predictions.csv")

    summary = {
        "feature_dir": str(config.feature_dir),
        "output_dir": str(config.output_dir),
        "models_seen": list(tables.keys()),
        "models_completed": int((metrics_df["status"] == "completed").sum()) if "status" in metrics_df else 0,
        "models_skipped": int((metrics_df["status"] == "skipped").sum()) if "status" in metrics_df else 0,
        "best_model": str(metrics_df.iloc[0]["model_name"]) if not metrics_df.empty else "",
        "best_g_mean": float(metrics_df.iloc[0]["g_mean"]) if not metrics_df.empty and pd.notna(metrics_df.iloc[0]["g_mean"]) else None,
    }
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
    return f"""# Modeling Report

## Summary

- Feature input directory: `{summary["feature_dir"]}`
- Output directory: `{summary["output_dir"]}`
- Models seen: {", ".join(summary["models_seen"])}
- Models completed: {summary["models_completed"]}
- Models skipped: {summary["models_skipped"]}
- {best_line}

## Notes

Logistic Regression uses `class_weight="balanced"` and patient-level cross-validation. LOOCV is used automatically for small feature tables; larger tables use stratified patient-level CV for computational practicality.

## Skipped Models

{skipped_lines}

## Outputs

- `model_cv_metrics.csv`
- `model_config_log.csv`
- `all_model_predictions.csv`
- `<model_name>_predictions.csv`
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
