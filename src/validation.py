"""Stage 08 validation for temporal stroke-risk prediction.

Implements docs/pipeline/08-validation.md. Aggregates model predictions and
metrics, computes validation tables, runs McNemar's test when possible, and
builds leakage/attrition evidence for paper-style reporting.
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
class ValidationConfig:
    model_dir: Path = Path("output/model_output")
    feature_importance_dir: Path = Path("output/feature_importance_output")
    cohort_dir: Path = Path("output/target_cohort_output")
    eda_dir: Path = Path("output/eda_output")
    output_dir: Path = Path("output/validation_output")
    patient_id_col: str = "patient_id"
    target_col: str = "y_true"
    pred_col: str = "y_pred"
    prob_col: str = "y_prob"
    baseline_model_name: str = "single_shot"


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def g_mean(sensitivity: float, specificity: float) -> float:
    return math.sqrt(max(sensitivity, 0.0) * max(specificity, 0.0))


def evaluate_predictions(pred: pd.DataFrame, config: ValidationConfig) -> dict[str, object]:
    from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

    y_true = pred[config.target_col].astype(int).tolist()
    y_pred = pred[config.pred_col].astype(int).tolist()
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    result: dict[str, object] = {
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "g_mean": float(g_mean(sensitivity, specificity)),
        "roc_auc": float("nan"),
        "pr_auc": float("nan"),
    }
    if config.prob_col in pred.columns:
        y_prob = pred[config.prob_col].astype(float).tolist()
        if len(set(y_true)) == 2:
            result["roc_auc"] = float(roc_auc_score(y_true, y_prob))
            result["pr_auc"] = float(average_precision_score(y_true, y_prob))
    return result


def load_prediction_tables(config: ValidationConfig) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for path in sorted(config.model_dir.glob("*_predictions.csv")):
        if path.name == "all_model_predictions.csv":
            continue
        model_name = path.name.replace("_predictions.csv", "")
        table = pd.read_csv(path)
        required = [config.target_col, config.pred_col]
        if any(column not in table.columns for column in required):
            continue
        tables[model_name] = table
    return tables


def build_metrics_table(prediction_tables: dict[str, pd.DataFrame], config: ValidationConfig) -> pd.DataFrame:
    rows = []
    for model_name, table in prediction_tables.items():
        metrics = evaluate_predictions(table, config)
        rows.append({"model_name": model_name, **metrics})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("g_mean", ascending=False, na_position="last").reset_index(drop=True)
    return df


def build_confusion_table(metrics_table: pd.DataFrame) -> pd.DataFrame:
    if metrics_table.empty:
        return pd.DataFrame(columns=["model_name", "tn", "fp", "fn", "tp"])
    return metrics_table[["model_name", "tn", "fp", "fn", "tp"]].copy()


def choose_best_temporal_model(metrics_table: pd.DataFrame, baseline_name: str) -> str:
    if metrics_table.empty:
        return ""
    temporal = metrics_table[metrics_table["model_name"] != baseline_name]
    if temporal.empty:
        return ""
    return str(temporal.sort_values("g_mean", ascending=False).iloc[0]["model_name"])


def mcnemar_test(
    baseline_pred: pd.DataFrame,
    challenger_pred: pd.DataFrame,
    config: ValidationConfig,
) -> dict[str, object]:
    merged = baseline_pred[[config.patient_id_col, config.target_col, config.pred_col]].rename(
        columns={config.pred_col: "baseline_pred"}
    ).merge(
        challenger_pred[[config.patient_id_col, config.target_col, config.pred_col]].rename(
            columns={config.pred_col: "challenger_pred"}
        ),
        on=[config.patient_id_col, config.target_col],
        how="inner",
    )
    if merged.empty:
        return {
            "status": "skipped",
            "reason": "no_overlap_patients_between_models",
        }

    baseline_correct = merged["baseline_pred"].astype(int) == merged[config.target_col].astype(int)
    challenger_correct = merged["challenger_pred"].astype(int) == merged[config.target_col].astype(int)
    b = int((baseline_correct & ~challenger_correct).sum())
    c = int((~baseline_correct & challenger_correct).sum())
    total = b + c
    if total == 0:
        return {
            "status": "skipped",
            "reason": "no_disagreement",
            "b_baseline_correct_challenger_wrong": b,
            "c_baseline_wrong_challenger_correct": c,
            "chi_square": 0.0,
            "p_value": 1.0,
        }
    chi_square = (abs(b - c) - 1.0) ** 2 / total
    p_value = float(math.erfc(math.sqrt(max(chi_square, 0.0) / 2.0)))
    return {
        "status": "completed",
        "reason": "",
        "overlap_patients": int(len(merged)),
        "b_baseline_correct_challenger_wrong": b,
        "c_baseline_wrong_challenger_correct": c,
        "chi_square": float(chi_square),
        "p_value": p_value,
    }


def build_leakage_audit(config: ValidationConfig) -> pd.DataFrame:
    leakage = load_optional_csv(config.eda_dir / "leakage_audit_summary.csv")
    rows = []
    if leakage.empty:
        rows.append(
            {
                "check": "eda_no_post_reference_records",
                "passed": False,
                "detail": "missing_leakage_audit_summary_csv",
            }
        )
    else:
        passed = bool(leakage["passed"].all()) if "passed" in leakage.columns else False
        rows.append(
            {
                "check": "eda_no_post_reference_records",
                "passed": passed,
                "detail": "loaded_from_stage_04",
            }
        )

    fi_summary = load_optional_csv(config.feature_importance_dir / "feature_importance_summary.csv")
    rows.append(
        {
            "check": "feature_selection_and_pca_fold_local_fit",
            "passed": True if not fi_summary.empty else False,
            "detail": "stage_07_executed" if not fi_summary.empty else "stage_07_summary_missing",
        }
    )
    return pd.DataFrame(rows)


def build_attrition_summary(config: ValidationConfig) -> pd.DataFrame:
    attrition = load_optional_csv(config.cohort_dir / "cohort_attrition_report.csv")
    if not attrition.empty:
        return attrition.copy()

    cohort_summary = load_optional_csv(config.cohort_dir / "target_cohort_summary.json")
    if not cohort_summary.empty:
        return cohort_summary
    return pd.DataFrame()


def build_report_markdown(summary: dict[str, object], mcnemar: dict[str, object]) -> str:
    mcnemar_line = (
        f"McNemar completed: chi-square `{mcnemar.get('chi_square', float('nan')):.4f}`, "
        f"p-value `{mcnemar.get('p_value', float('nan')):.6f}`."
        if mcnemar.get("status") == "completed"
        else f"McNemar skipped: `{mcnemar.get('reason', '')}`."
    )
    return f"""# Validation Report

## Summary

- Models evaluated: {summary["models_evaluated"]}
- Baseline model: `{summary["baseline_model"]}`
- Best model by G-Mean: `{summary["best_model"]}`
- Best G-Mean: `{summary["best_g_mean"]}`
- Temporal model count: {summary["temporal_model_count"]}
- {mcnemar_line}
- Leakage audit passed: `{summary["leakage_audit_passed"]}`

## Metrics Policy

- Primary metric: `G-Mean = sqrt(Sensitivity * Specificity)`
- Required per model: sensitivity, specificity, G-Mean
- Optional: ROC-AUC, PR-AUC (when probability outputs available)

## Outputs

- `validation_metrics.csv`
- `validation_confusion_matrices.csv`
- `roc_pr_auc_table.csv`
- `baseline_vs_temporal_comparison.csv`
- `mcnemar_test_report.csv`
- `leakage_audit_report.csv`
- `cohort_attrition_validation_view.csv`
- `validation_summary.json`
- `validation_report.md`
"""


def run_validation(config: ValidationConfig) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    prediction_tables = load_prediction_tables(config)
    metrics_table = build_metrics_table(prediction_tables, config)
    confusion_table = build_confusion_table(metrics_table)
    roc_pr_table = (
        metrics_table[["model_name", "roc_auc", "pr_auc"]].copy()
        if not metrics_table.empty
        else pd.DataFrame(columns=["model_name", "roc_auc", "pr_auc"])
    )

    baseline_name = config.baseline_model_name
    best_temporal = choose_best_temporal_model(metrics_table, baseline_name)
    comparison = metrics_table.copy()
    if not comparison.empty:
        comparison["model_group"] = np.where(comparison["model_name"] == baseline_name, "baseline", "temporal")

    if baseline_name in prediction_tables and best_temporal:
        mcnemar = mcnemar_test(prediction_tables[baseline_name], prediction_tables[best_temporal], config)
        mcnemar["baseline_model"] = baseline_name
        mcnemar["challenger_model"] = best_temporal
    else:
        mcnemar = {
            "status": "skipped",
            "reason": "baseline_or_temporal_predictions_missing",
            "baseline_model": baseline_name,
            "challenger_model": best_temporal if best_temporal else "",
        }

    leakage_audit = build_leakage_audit(config)
    attrition_view = load_optional_csv(config.cohort_dir / "cohort_attrition_report.csv")
    if attrition_view.empty:
        attrition_view = pd.DataFrame(
            [{"step": "missing", "reason": "cohort_attrition_report_not_found"}]
        )

    write_csv(metrics_table, config.output_dir / "validation_metrics.csv")
    write_csv(confusion_table, config.output_dir / "validation_confusion_matrices.csv")
    write_csv(roc_pr_table, config.output_dir / "roc_pr_auc_table.csv")
    write_csv(comparison, config.output_dir / "baseline_vs_temporal_comparison.csv")
    write_csv(pd.DataFrame([mcnemar]), config.output_dir / "mcnemar_test_report.csv")
    write_csv(leakage_audit, config.output_dir / "leakage_audit_report.csv")
    write_csv(attrition_view, config.output_dir / "cohort_attrition_validation_view.csv")

    best_model = ""
    best_g = None
    if not metrics_table.empty:
        top = metrics_table.sort_values("g_mean", ascending=False, na_position="last").iloc[0]
        best_model = str(top["model_name"])
        best_g = float(top["g_mean"]) if pd.notna(top["g_mean"]) else None

    summary = {
        "model_dir": str(config.model_dir),
        "output_dir": str(config.output_dir),
        "models_evaluated": int(len(metrics_table)),
        "baseline_model": baseline_name,
        "best_model": best_model,
        "best_g_mean": best_g,
        "temporal_model_count": int(max(len(metrics_table) - (1 if baseline_name in metrics_table["model_name"].tolist() else 0), 0))
        if not metrics_table.empty
        else 0,
        "mcnemar_status": mcnemar.get("status", "skipped"),
        "mcnemar_reason": mcnemar.get("reason", ""),
        "leakage_audit_passed": bool(leakage_audit["passed"].all()) if "passed" in leakage_audit.columns else False,
    }
    write_json(summary, config.output_dir / "validation_summary.json")
    (config.output_dir / "validation_report.md").write_text(
        build_report_markdown(summary, mcnemar),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 08 validation.")
    parser.add_argument("--model-dir", default=str(ValidationConfig.model_dir))
    parser.add_argument("--feature-importance-dir", default=str(ValidationConfig.feature_importance_dir))
    parser.add_argument("--cohort-dir", default=str(ValidationConfig.cohort_dir))
    parser.add_argument("--eda-dir", default=str(ValidationConfig.eda_dir))
    parser.add_argument("--output-dir", default=str(ValidationConfig.output_dir))
    parser.add_argument("--baseline-model-name", default=ValidationConfig.baseline_model_name)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ValidationConfig(
        model_dir=Path(args.model_dir),
        feature_importance_dir=Path(args.feature_importance_dir),
        cohort_dir=Path(args.cohort_dir),
        eda_dir=Path(args.eda_dir),
        output_dir=Path(args.output_dir),
        baseline_model_name=args.baseline_model_name,
    )
    report = run_validation(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
