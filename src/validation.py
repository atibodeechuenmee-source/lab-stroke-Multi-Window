from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from modeling import Config as ModelingConfig
from modeling import get_feature_columns, load_feature_table, make_models, split_patient_level_data


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sns.set_theme(style="whitegrid")


@dataclass(frozen=True)
class Config:
    feature_table_path: Path = Path("data/processed/patient_level_90d_stroke.csv")
    model_output_dir: Path = Path("output/model_output")
    output_dir: Path = Path("output/validation_output")
    target_column: str = "stroke_3m"
    random_state: int = 42
    test_size: float = 0.25
    calibration_bins: int = 10


def load_best_model_name(config: Config, available_models: set[str]) -> str:
    report_path = config.model_output_dir / "patient_level_90d_model_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        best_model = report.get("best_model_by_pr_auc")
        if best_model in available_models:
            return str(best_model)

    metrics_path = config.model_output_dir / "patient_level_90d_holdout_metrics.csv"
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        ranked = metrics[metrics["model"].isin(available_models)].sort_values(["pr_auc", "roc_auc"], ascending=False)
        if not ranked.empty:
            return str(ranked.iloc[0]["model"])

    return sorted(available_models)[0]


def train_best_model(X_train: pd.DataFrame, y_train: pd.Series, config: Config):
    modeling_config = ModelingConfig(
        feature_table_path=config.feature_table_path,
        output_dir=config.model_output_dir,
        target_column=config.target_column,
        random_state=config.random_state,
        test_size=config.test_size,
    )
    models = make_models(y_train, modeling_config)
    best_model_name = load_best_model_name(config, set(models))
    model = models[best_model_name]
    print(f"Training validation model: {best_model_name}")
    model.fit(X_train, y_train)
    return best_model_name, model


def metric_row(y_true: pd.Series, y_score, threshold: float) -> dict[str, float]:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
        "predicted_positive": int(tp + fp),
    }


def build_threshold_analysis(y_true: pd.Series, y_score, config: Config) -> pd.DataFrame:
    thresholds = sorted(set([0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]))
    threshold_df = pd.DataFrame([metric_row(y_true, y_score, threshold) for threshold in thresholds])

    threshold_path = config.output_dir / "patient_level_90d_threshold_analysis.csv"
    threshold_df.to_csv(threshold_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(8, 5))
    plot_df = threshold_df.melt(
        id_vars="threshold",
        value_vars=["precision", "recall", "f1"],
        var_name="metric",
        value_name="value",
    )
    sns.lineplot(data=plot_df, x="threshold", y="value", hue="metric", marker="o")
    plt.ylim(0, 1)
    plt.title("Threshold Analysis: Patient-Level 90-Day Stroke")
    plt.tight_layout()
    plt.savefig(config.output_dir / "patient_level_90d_threshold_analysis.png", dpi=300, bbox_inches="tight")
    plt.close()
    return threshold_df


def build_calibration_summary(y_true: pd.Series, y_score, config: Config) -> pd.DataFrame:
    prob_true, prob_pred = calibration_curve(
        y_true,
        y_score,
        n_bins=config.calibration_bins,
        strategy="quantile",
    )
    calibration_df = pd.DataFrame(
        {
            "bin": range(1, len(prob_true) + 1),
            "mean_predicted_probability": prob_pred,
            "observed_event_rate": prob_true,
            "absolute_error": abs(prob_true - prob_pred),
        }
    )
    calibration_df.to_csv(
        config.output_dir / "patient_level_90d_calibration_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    plt.figure(figsize=(6, 6))
    plt.plot([0, 1], [0, 1], linestyle="--", color="#777777", label="Perfect calibration")
    plt.plot(prob_pred, prob_true, marker="o", label="Model")
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Observed event rate")
    plt.title("Calibration Curve: Patient-Level 90-Day Stroke")
    plt.legend()
    plt.tight_layout()
    plt.savefig(config.output_dir / "patient_level_90d_calibration_curve.png", dpi=300, bbox_inches="tight")
    plt.close()
    return calibration_df


def build_leakage_audit(feature_columns: list[str], config: Config) -> pd.DataFrame:
    forbidden_columns = {"hn", "index_date", "event_date", "days_to_event", config.target_column}
    risky_terms = ("stroke", "diagnosis", "event", "future", "after_index", "post_index", "days_to_event")
    rows = []

    for feature in feature_columns:
        lower = feature.lower()
        flags = []
        if feature in forbidden_columns:
            flags.append("forbidden_identifier_or_target")
        if any(term in lower for term in risky_terms):
            flags.append("name_contains_possible_leakage_term")
        if feature in {"index_year", "index_month"}:
            flags.append("calendar_feature_monitor_for_temporal_drift")
        rows.append(
            {
                "feature": feature,
                "status": "review" if flags else "pass",
                "flags": "; ".join(flags),
            }
        )

    audit_df = pd.DataFrame(rows)
    audit_df.to_csv(config.output_dir / "patient_level_90d_leakage_audit.csv", index=False, encoding="utf-8-sig")
    return audit_df


def write_holdout_predictions(
    hn_test: pd.Series,
    y_test: pd.Series,
    y_score,
    best_model_name: str,
    config: Config,
) -> pd.DataFrame:
    prediction_df = pd.DataFrame(
        {
            "hn": hn_test.values,
            "model": best_model_name,
            "stroke_3m_true": y_test.values,
            "stroke_3m_probability": y_score,
            "stroke_3m_pred_0_5": (y_score >= 0.5).astype(int),
        },
        index=y_test.index,
    ).sort_values("stroke_3m_probability", ascending=False)
    prediction_df.to_csv(
        config.output_dir / "patient_level_90d_holdout_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return prediction_df


def recommendation_from_metrics(holdout_metrics: dict[str, float], threshold_row: dict[str, float]) -> str:
    if holdout_metrics["pr_auc"] < 0.30 or threshold_row["precision"] < 0.20:
        return "Not ready for clinical decision-making; suitable for research reporting and workflow iteration only."
    if threshold_row["recall"] >= 0.70 and threshold_row["precision"] >= 0.20:
        return "Candidate screening model; requires external validation and threshold review before operational use."
    return "Candidate model with limited utility; improve calibration and threshold policy before use."


def write_validation_report(
    best_model_name: str,
    patient_df: pd.DataFrame,
    y_test: pd.Series,
    y_score,
    threshold_df: pd.DataFrame,
    calibration_df: pd.DataFrame,
    audit_df: pd.DataFrame,
    config: Config,
) -> dict[str, object]:
    threshold_0_5 = threshold_df.loc[threshold_df["threshold"] == 0.50].iloc[0].to_dict()
    holdout_metrics = {
        "roc_auc": roc_auc_score(y_test, y_score),
        "pr_auc": average_precision_score(y_test, y_score),
        "brier_score": brier_score_loss(y_test, y_score),
        "prevalence": float(y_test.mean()),
    }
    best_f1 = threshold_df.sort_values(["f1", "recall"], ascending=False).iloc[0].to_dict()
    high_recall = threshold_df[threshold_df["recall"] >= 0.80]
    recall_threshold = None if high_recall.empty else high_recall.sort_values("precision", ascending=False).iloc[0].to_dict()
    review_features = audit_df[audit_df["status"] == "review"]["feature"].tolist()
    recommendation = recommendation_from_metrics(holdout_metrics, threshold_0_5)

    payload: dict[str, object] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "target": config.target_column,
        "unit_of_analysis": "patient",
        "model": best_model_name,
        "patient_rows": int(len(patient_df)),
        "holdout_rows": int(len(y_test)),
        "holdout_positive_patients": int(y_test.sum()),
        "holdout_prevalence_percent": round(float(y_test.mean() * 100), 2),
        "holdout_metrics": holdout_metrics,
        "threshold_0_5": threshold_0_5,
        "best_f1_threshold": best_f1,
        "high_recall_threshold": recall_threshold,
        "calibration_mean_absolute_error": float(calibration_df["absolute_error"].mean()),
        "leakage_audit_review_features": review_features,
        "recommendation": recommendation,
        "limitations": [
            "Validation uses an internal holdout split, not an external hospital or future-time validation cohort.",
            "Threshold choice changes the precision-recall tradeoff and should be tied to the clinical use case.",
            "Predicted probabilities need calibration review before use as absolute risk estimates.",
            "Feature importance and validation metrics do not prove causal relationships.",
        ],
        "outputs": {
            "validation_report_txt": str(config.output_dir / "patient_level_90d_validation_report.txt"),
            "validation_report_json": str(config.output_dir / "patient_level_90d_validation_report.json"),
            "holdout_predictions": str(config.output_dir / "patient_level_90d_holdout_predictions.csv"),
            "threshold_analysis": str(config.output_dir / "patient_level_90d_threshold_analysis.csv"),
            "calibration_summary": str(config.output_dir / "patient_level_90d_calibration_summary.csv"),
            "leakage_audit": str(config.output_dir / "patient_level_90d_leakage_audit.csv"),
        },
    }

    json_path = config.output_dir / "patient_level_90d_validation_report.json"
    txt_path = config.output_dir / "patient_level_90d_validation_report.txt"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    with txt_path.open("w", encoding="utf-8") as file:
        file.write("Patient-Level 90-Day Stroke Validation Report\n")
        file.write("=============================================\n\n")
        file.write(f"Target: {config.target_column}\n")
        file.write("Unit of analysis: patient\n")
        file.write(f"Validated model: {best_model_name}\n")
        file.write(f"Holdout rows: {payload['holdout_rows']:,}\n")
        file.write(f"Holdout positives: {payload['holdout_positive_patients']:,}\n")
        file.write(f"Holdout prevalence: {payload['holdout_prevalence_percent']}%\n\n")
        file.write("Holdout Metrics\n")
        file.write("---------------\n")
        file.write(f"ROC-AUC: {holdout_metrics['roc_auc']:.4f}\n")
        file.write(f"PR-AUC: {holdout_metrics['pr_auc']:.4f}\n")
        file.write(f"Brier score: {holdout_metrics['brier_score']:.4f}\n\n")
        file.write("Threshold 0.50\n")
        file.write("--------------\n")
        file.write(f"Precision: {threshold_0_5['precision']:.4f}\n")
        file.write(f"Recall: {threshold_0_5['recall']:.4f}\n")
        file.write(f"F1: {threshold_0_5['f1']:.4f}\n")
        file.write(
            "Confusion matrix [[TN, FP], [FN, TP]]: "
            f"[[{threshold_0_5['true_negative']}, {threshold_0_5['false_positive']}], "
            f"[{threshold_0_5['false_negative']}, {threshold_0_5['true_positive']}]]\n\n"
        )
        file.write("Recommendation\n")
        file.write("--------------\n")
        file.write(f"{recommendation}\n\n")
        file.write("Leakage Audit\n")
        file.write("-------------\n")
        if review_features:
            file.write("Features requiring review: " + ", ".join(review_features) + "\n\n")
        else:
            file.write("No feature names matched the configured leakage-risk terms.\n\n")
        file.write("Limitations\n")
        file.write("-----------\n")
        for limitation in payload["limitations"]:
            file.write(f"- {limitation}\n")

    return payload


def run(config: Config) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    modeling_config = ModelingConfig(
        feature_table_path=config.feature_table_path,
        output_dir=config.model_output_dir,
        target_column=config.target_column,
        random_state=config.random_state,
        test_size=config.test_size,
    )
    patient_df = load_feature_table(modeling_config)
    feature_columns = get_feature_columns(patient_df, modeling_config)
    X = patient_df[feature_columns]
    y = patient_df[config.target_column]
    hn = patient_df["hn"]

    X_train, X_test, y_train, y_test, _, hn_test = split_patient_level_data(X, y, hn, modeling_config)
    best_model_name, model = train_best_model(X_train, y_train, config)
    y_score = model.predict_proba(X_test)[:, 1]

    write_holdout_predictions(hn_test, y_test, y_score, best_model_name, config)
    threshold_df = build_threshold_analysis(y_test, y_score, config)
    calibration_df = build_calibration_summary(y_test, y_score, config)
    audit_df = build_leakage_audit(feature_columns, config)

    return write_validation_report(
        best_model_name=best_model_name,
        patient_df=patient_df,
        y_test=y_test,
        y_score=y_score,
        threshold_df=threshold_df,
        calibration_df=calibration_df,
        audit_df=audit_df,
        config=config,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the patient-level 90-day stroke prediction workflow.")
    parser.add_argument("--feature-table", default=str(Config.feature_table_path), help="Patient-level feature table CSV.")
    parser.add_argument("--model-output-dir", default=str(Config.model_output_dir), help="Directory with modeling outputs.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Validation output directory.")
    parser.add_argument("--test-size", type=float, default=Config.test_size, help="Holdout test fraction.")
    parser.add_argument("--calibration-bins", type=int, default=Config.calibration_bins, help="Calibration bins.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        feature_table_path=Path(args.feature_table),
        model_output_dir=Path(args.model_output_dir),
        output_dir=Path(args.output_dir),
        test_size=args.test_size,
        calibration_bins=args.calibration_bins,
    )
    payload = run(config)
    print("Validation completed")
    print(f"Model: {payload['model']}")
    print(f"PR-AUC: {payload['holdout_metrics']['pr_auc']:.4f}")
    print(f"Recommendation: {payload['recommendation']}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
