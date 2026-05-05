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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sns.set_theme(style="whitegrid")


@dataclass(frozen=True)
class Config:
    feature_table_path: Path = Path("data/processed/patient_level_90d_stroke.csv")
    output_dir: Path = Path("output/model_output")
    target_column: str = "stroke_3m"
    random_state: int = 42
    test_size: float = 0.25
    cv_splits: int = 5


EXCLUDED_MODEL_COLUMNS = {"hn", "index_date", "event_date", "days_to_event", "stroke_3m"}


def load_feature_table(config: Config) -> pd.DataFrame:
    if not config.feature_table_path.exists():
        raise FileNotFoundError(f"Feature table not found: {config.feature_table_path}")
    patient_df = pd.read_csv(config.feature_table_path)
    if config.target_column not in patient_df.columns:
        raise KeyError(f"Missing target column: {config.target_column}")
    if "hn" not in patient_df.columns:
        raise KeyError("Missing patient id column: hn")
    return patient_df


def get_feature_columns(patient_df: pd.DataFrame, config: Config) -> list[str]:
    excluded = set(EXCLUDED_MODEL_COLUMNS)
    excluded.add(config.target_column)
    return [column for column in patient_df.columns if column not in excluded]


def make_models(y: pd.Series, config: Config) -> dict[str, Pipeline]:
    positive = int(y.sum())
    negative = int((y == 0).sum())
    scale_pos_weight = negative / max(positive, 1)

    models: dict[str, Pipeline] = {
        "logistic_regression": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=config.random_state,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=3,
                        min_samples_split=8,
                        max_features="sqrt",
                        class_weight="balanced_subsample",
                        random_state=config.random_state,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
    }

    if XGBClassifier is not None:
        models["xgboost"] = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "classifier",
                    XGBClassifier(
                        n_estimators=300,
                        max_depth=3,
                        learning_rate=0.04,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        min_child_weight=5,
                        reg_lambda=2.0,
                        objective="binary:logistic",
                        eval_metric="aucpr",
                        tree_method="hist",
                        scale_pos_weight=scale_pos_weight,
                        random_state=config.random_state,
                        n_jobs=1,
                    ),
                ),
            ]
        )

    return models


def predict(model: Pipeline, X: pd.DataFrame):
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]
    return y_pred, y_proba


def compute_metrics(y_true: pd.Series, y_pred, y_proba) -> dict[str, float]:
    return {
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def split_patient_level_data(X: pd.DataFrame, y: pd.Series, hn: pd.Series, config: Config):
    X_train, X_test, y_train, y_test, hn_train, hn_test = train_test_split(
        X,
        y,
        hn,
        test_size=config.test_size,
        stratify=y,
        random_state=config.random_state,
    )
    overlap = set(hn_train).intersection(set(hn_test))
    if overlap:
        raise ValueError(f"Patient leakage detected: {len(overlap)} hn values exist in both train and test")
    return X_train, X_test, y_train, y_test, hn_train, hn_test


def run_cv(models: dict[str, Pipeline], X: pd.DataFrame, y: pd.Series, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    cv = StratifiedKFold(n_splits=config.cv_splits, shuffle=True, random_state=config.random_state)
    rows = []

    for model_name, model in models.items():
        print(f"Running CV: {model_name}")
        for fold, (train_idx, valid_idx) in enumerate(cv.split(X, y), start=1):
            X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
            y_train, y_valid = y.iloc[train_idx], y.iloc[valid_idx]
            model.fit(X_train, y_train)
            y_pred, y_proba = predict(model, X_valid)
            rows.append({"model": model_name, "fold": fold, **compute_metrics(y_valid, y_pred, y_proba)})

    cv_df = pd.DataFrame(rows)
    summary = cv_df.groupby("model")[["roc_auc", "pr_auc", "precision", "recall", "f1"]].agg(["mean", "std"])
    summary.columns = ["_".join(column).strip("_") for column in summary.columns]
    summary = summary.reset_index()
    return cv_df, summary


def plot_confusion_matrix(cm, model_name: str, config: Config) -> None:
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.title(f"Confusion Matrix: {model_name}")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    path = config.output_dir / f"patient_level_90d_confusion_matrix_{model_name}.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def train_holdout(models: dict[str, Pipeline], X_train, X_test, y_train, y_test, config: Config):
    fitted = {}
    rows = []
    reports = {}

    for model_name, model in models.items():
        print(f"Training holdout model: {model_name}")
        model.fit(X_train, y_train)
        y_pred, y_proba = predict(model, X_test)
        metrics = compute_metrics(y_test, y_pred, y_proba)
        cm = confusion_matrix(y_test, y_pred)
        plot_confusion_matrix(cm, model_name, config)
        rows.append({"model": model_name, **metrics})
        fitted[model_name] = model
        reports[model_name] = {
            "confusion_matrix": cm.tolist(),
            "classification_report": classification_report(y_test, y_pred, digits=4, output_dict=True),
            "classification_report_text": classification_report(y_test, y_pred, digits=4),
        }

    metrics_df = pd.DataFrame(rows).sort_values(["pr_auc", "roc_auc"], ascending=False)
    return fitted, metrics_df, reports


def write_outputs(
    patient_df: pd.DataFrame,
    feature_columns: list[str],
    cv_df: pd.DataFrame,
    cv_summary: pd.DataFrame,
    holdout_metrics: pd.DataFrame,
    reports: dict,
    config: Config,
) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "cv_metrics": config.output_dir / "patient_level_90d_cv_metrics.csv",
        "cv_metrics_summary": config.output_dir / "patient_level_90d_cv_metrics_summary.csv",
        "holdout_metrics": config.output_dir / "patient_level_90d_holdout_metrics.csv",
        "model_report_txt": config.output_dir / "patient_level_90d_model_report.txt",
        "model_report_json": config.output_dir / "patient_level_90d_model_report.json",
    }

    cv_df.to_csv(paths["cv_metrics"], index=False, encoding="utf-8-sig")
    cv_summary.to_csv(paths["cv_metrics_summary"], index=False, encoding="utf-8-sig")
    holdout_metrics.to_csv(paths["holdout_metrics"], index=False, encoding="utf-8-sig")

    payload: dict[str, object] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "feature_table_path": str(config.feature_table_path),
        "target": config.target_column,
        "unit_of_analysis": "patient",
        "patient_rows": int(len(patient_df)),
        "positive_patients": int(patient_df[config.target_column].sum()),
        "negative_patients": int((patient_df[config.target_column] == 0).sum()),
        "prevalence_percent": round(float(patient_df[config.target_column].mean() * 100), 2),
        "model_feature_count": len(feature_columns),
        "models": holdout_metrics["model"].tolist(),
        "best_model_by_pr_auc": holdout_metrics.iloc[0]["model"],
        "outputs": {key: str(path) for key, path in paths.items()},
        "checks": {
            "preprocessing_fit_inside_pipeline": True,
            "patient_level_split": True,
            "target": config.target_column,
            "test_set_used_for_final_evaluation_only": True,
        },
        "classification_reports": reports,
    }
    paths["model_report_json"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    with paths["model_report_txt"].open("w", encoding="utf-8") as file:
        file.write("Patient-Level 90-Day Stroke Modeling Report\n")
        file.write("===========================================\n\n")
        file.write("Target: stroke_3m\n")
        file.write("Unit of analysis: patient\n")
        file.write(f"Rows: {payload['patient_rows']:,}\n")
        file.write(f"Positive: {payload['positive_patients']:,}\n")
        file.write(f"Negative: {payload['negative_patients']:,}\n")
        file.write(f"Prevalence: {payload['prevalence_percent']}%\n")
        file.write(f"Model features: {payload['model_feature_count']:,}\n")
        file.write(f"Best model by PR-AUC: {payload['best_model_by_pr_auc']}\n\n")
        file.write("CV Summary\n----------\n")
        file.write(cv_summary.to_string(index=False))
        file.write("\n\nHoldout Metrics\n---------------\n")
        file.write(holdout_metrics.to_string(index=False))
        file.write("\n\n")
        for model_name, detail in reports.items():
            file.write(f"Confusion Matrix: {model_name}\n")
            file.write(str(detail["confusion_matrix"]))
            file.write("\n\n")
            file.write(detail["classification_report_text"])
            file.write("\n\n")

    return payload


def run(config: Config) -> dict[str, object]:
    patient_df = load_feature_table(config)
    feature_columns = get_feature_columns(patient_df, config)
    X = patient_df[feature_columns]
    y = patient_df[config.target_column]
    hn = patient_df["hn"]

    if y.nunique() < 2:
        raise ValueError("The patient-level feature table has only one class. Cannot train classifiers.")

    X_train, X_test, y_train, y_test, _, _ = split_patient_level_data(X, y, hn, config)
    models = make_models(y, config)
    cv_df, cv_summary = run_cv(models, X_train, y_train, config)

    holdout_models = make_models(y_train, config)
    _, holdout_metrics, reports = train_holdout(holdout_models, X_train, X_test, y_train, y_test, config)
    return write_outputs(patient_df, feature_columns, cv_df, cv_summary, holdout_metrics, reports, config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train patient-level 90-day stroke prediction models.")
    parser.add_argument("--feature-table", default=str(Config.feature_table_path), help="Patient-level feature table CSV.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Model output directory.")
    parser.add_argument("--test-size", type=float, default=Config.test_size, help="Holdout test fraction.")
    parser.add_argument("--cv-splits", type=int, default=Config.cv_splits, help="Number of CV folds.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        feature_table_path=Path(args.feature_table),
        output_dir=Path(args.output_dir),
        test_size=args.test_size,
        cv_splits=args.cv_splits,
    )
    payload = run(config)
    print("Modeling completed")
    print(f"Rows: {payload['patient_rows']:,}")
    print(f"Positive patients: {payload['positive_patients']:,}")
    print(f"Best model by PR-AUC: {payload['best_model_by_pr_auc']}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
