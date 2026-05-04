# =========================
# Patient-Level 90-Day Stroke Prediction
# =========================
#
# Research-oriented pipeline for predicting whether a patient will have a
# primary stroke diagnosis within 90 days. This script builds a patient-level
# cohort, engineers historical features from visits before the index date,
# compares Logistic Regression, RandomForest, and XGBoost, and exports SHAP
# explanations for the best tree-based model.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import warnings

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
    import shap
except ImportError:  # pragma: no cover
    shap = None

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore", category=UserWarning)
sns.set_theme(style="whitegrid")


@dataclass(frozen=True)
class Config:
    data_path: Path = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
    processed_path: Path = Path("data/processed/patient_level_90d_stroke.csv")
    output_dir: Path = Path("output") / "model_output"
    random_state: int = 42
    horizon_days: int = 90
    test_size: float = 0.25
    cv_splits: int = 5
    cv_max_rows: int = 60000
    shap_sample_size: int = 1000


CONFIG = Config()
CONFIG.output_dir.mkdir(parents=True, exist_ok=True)
CONFIG.processed_path.parent.mkdir(parents=True, exist_ok=True)

STROKE_PATTERN = re.compile(r"^I6[0-9][0-9A-Z]*$", re.IGNORECASE)

LATEST_FEATURES = [
    "sex",
    "age",
    "height",
    "bw",
    "bmi",
    "smoke",
    "drinking",
    "AF",
    "heart_disease",
    "hypertension",
    "diabetes",
    "Statin",
    "Gemfibrozil",
    "Antihypertensive_flag",
]

TEMPORAL_FEATURES = [
    "bps",
    "bpd",
    "HDL",
    "LDL",
    "Triglyceride",
    "Cholesterol",
    "FBS",
    "eGFR",
    "Creatinine",
    "TC:HDL_ratio",
]


def build_stroke_flag(df: pd.DataFrame) -> pd.Series:
    """Create stroke event flag from primary diagnosis ICD-10 I60-I69*."""
    diagnosis = df["PrincipleDiagnosis"].astype("string").str.strip().fillna("")
    return diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def load_raw_data(config: Config) -> pd.DataFrame:
    """Load raw Excel data and normalize date/target columns."""
    print(f"Loading raw data: {config.data_path}")
    df = pd.read_excel(config.data_path)
    df["vstdate"] = pd.to_datetime(df["vstdate"], errors="coerce")
    df = df.dropna(subset=["hn", "vstdate"]).copy()
    df["stroke_event"] = build_stroke_flag(df)
    df = df.sort_values(["hn", "vstdate"]).reset_index(drop=True)
    print(f"Raw rows after required fields: {len(df):,}")
    return df


def choose_index_record(group: pd.DataFrame, max_date: pd.Timestamp, config: Config):
    """
    Select exactly one index visit per patient.

    Positive patient:
      - first primary stroke date is the event date
      - index date is the latest visit before event date
      - include only if event occurs within 1-90 days after index

    Negative patient:
      - no primary stroke event in observed data
      - index date is the latest visit with at least 90 days of observable follow-up
    """
    group = group.sort_values("vstdate")
    stroke_rows = group[group["stroke_event"] == 1]

    if not stroke_rows.empty:
        event_date = stroke_rows["vstdate"].min()
        prior_rows = group[group["vstdate"] < event_date]
        if prior_rows.empty:
            return None

        index_row = prior_rows.iloc[-1]
        days_to_event = (event_date - index_row["vstdate"]).days
        if 1 <= days_to_event <= config.horizon_days:
            return {
                "hn": index_row["hn"],
                "index_date": index_row["vstdate"],
                "event_date": event_date,
                "days_to_event": days_to_event,
                "stroke_3m": 1,
            }
        return None

    eligible = group[group["vstdate"] <= max_date - pd.Timedelta(days=config.horizon_days)]
    if eligible.empty:
        return None

    index_row = eligible.iloc[-1]
    return {
        "hn": index_row["hn"],
        "index_date": index_row["vstdate"],
        "event_date": pd.NaT,
        "days_to_event": pd.NA,
        "stroke_3m": 0,
    }


def make_feature_row(history: pd.DataFrame, cohort_row: dict) -> dict:
    """Aggregate all patient history up to and including index_date."""
    row = {
        "hn": cohort_row["hn"],
        "index_date": cohort_row["index_date"],
        "event_date": cohort_row["event_date"],
        "days_to_event": cohort_row["days_to_event"],
        "stroke_3m": cohort_row["stroke_3m"],
        "history_visit_count": len(history),
        "history_days_observed": (history["vstdate"].max() - history["vstdate"].min()).days,
    }

    latest = history.iloc[-1]
    for col in LATEST_FEATURES:
        if col in history.columns:
            row[f"{col}_latest"] = latest[col]

    for col in TEMPORAL_FEATURES:
        if col not in history.columns:
            continue
        values = history[col]
        row[f"{col}_latest"] = values.iloc[-1]
        row[f"{col}_mean"] = values.mean()
        row[f"{col}_min"] = values.min()
        row[f"{col}_max"] = values.max()
        row[f"{col}_std"] = values.std()
        row[f"{col}_count"] = values.notna().sum()
        row[f"{col}_missing_rate"] = values.isna().mean()

    return row


def build_patient_level_dataset(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Build patient-level 90-day prediction dataset."""
    max_date = df["vstdate"].max()
    rows = []
    excluded_positive_no_prior = 0
    excluded_not_in_horizon = 0
    excluded_no_followup = 0

    for _, group in df.groupby("hn", sort=False):
        cohort_row = choose_index_record(group, max_date, config)
        if cohort_row is None:
            if group["stroke_event"].any():
                stroke_date = group.loc[group["stroke_event"] == 1, "vstdate"].min()
                prior = group[group["vstdate"] < stroke_date]
                if prior.empty:
                    excluded_positive_no_prior += 1
                else:
                    excluded_not_in_horizon += 1
            else:
                excluded_no_followup += 1
            continue

        history = group[group["vstdate"] <= cohort_row["index_date"]]
        rows.append(make_feature_row(history, cohort_row))

    patient_df = pd.DataFrame(rows)
    patient_df.to_csv(config.processed_path, index=False, encoding="utf-8-sig")
    print(f"Saved processed patient-level dataset: {config.processed_path}")
    print(f"Patient-level rows: {len(patient_df):,}")
    print(f"Positive rows: {int(patient_df['stroke_3m'].sum()):,}")
    print(f"Negative rows: {int((patient_df['stroke_3m'] == 0).sum()):,}")
    print(f"Excluded positives without prior visit: {excluded_positive_no_prior:,}")
    print(f"Excluded positives outside {config.horizon_days}d horizon: {excluded_not_in_horizon:,}")
    print(f"Excluded negatives without follow-up: {excluded_no_followup:,}")
    return patient_df


def get_feature_columns(patient_df: pd.DataFrame) -> list[str]:
    """Return model feature columns while excluding identifiers/outcome columns."""
    excluded = {"hn", "index_date", "event_date", "days_to_event", "stroke_3m"}
    return [col for col in patient_df.columns if col not in excluded]


def make_models(y: pd.Series, config: Config) -> dict[str, Pipeline]:
    """Create candidate models with preprocessing inside each pipeline."""
    positive = int(y.sum())
    negative = int((y == 0).sum())
    scale_pos_weight = negative / max(positive, 1)

    models = {
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
    """Return predicted labels and positive-class probabilities."""
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]
    return y_pred, y_proba


def compute_metrics(y_true: pd.Series, y_pred, y_proba) -> dict[str, float]:
    """Compute metrics suited for imbalanced clinical prediction."""
    return {
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def run_cv(models: dict[str, Pipeline], X: pd.DataFrame, y: pd.Series, config: Config) -> pd.DataFrame:
    """Run patient-level Stratified K-Fold CV."""
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
    cv_path = config.output_dir / "patient_level_90d_cv_metrics.csv"
    cv_df.to_csv(cv_path, index=False, encoding="utf-8-sig")
    summary = cv_df.groupby("model")[["roc_auc", "pr_auc", "precision", "recall", "f1"]].agg(["mean", "std"])
    summary.columns = ["_".join(col).strip("_") for col in summary.columns]
    summary = summary.reset_index()
    summary_path = config.output_dir / "patient_level_90d_cv_metrics_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"Saved CV metrics: {cv_path}")
    print(f"Saved CV summary: {summary_path}")
    return summary


def plot_confusion_matrix(cm, model_name: str, config: Config) -> None:
    """Save confusion matrix heatmap for one model."""
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
    """Train final holdout models and export metrics."""
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
            "confusion_matrix": cm,
            "classification_report": classification_report(y_test, y_pred, digits=4),
        }

    metrics_df = pd.DataFrame(rows).sort_values(["pr_auc", "roc_auc"], ascending=False)
    metrics_path = config.output_dir / "patient_level_90d_holdout_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    print(f"Saved holdout metrics: {metrics_path}")
    return fitted, metrics_df, reports


def transformed_feature_names(model: Pipeline, feature_columns: list[str]) -> list[str]:
    """Return feature names after imputation and missing indicators."""
    imputer = model.named_steps["imputer"]
    return list(imputer.get_feature_names_out(feature_columns))


def export_feature_importance(fitted: dict[str, Pipeline], feature_columns: list[str], config: Config) -> pd.DataFrame:
    """Export model-native feature importance for tree-based models."""
    frames = []
    for model_name, model in fitted.items():
        classifier = model.named_steps["classifier"]
        if not hasattr(classifier, "feature_importances_"):
            continue
        frames.append(
            pd.DataFrame(
                {
                    "model": model_name,
                    "feature": transformed_feature_names(model, feature_columns),
                    "importance": classifier.feature_importances_,
                }
            )
        )

    if not frames:
        return pd.DataFrame()

    importance_df = pd.concat(frames, ignore_index=True).sort_values(["model", "importance"], ascending=[True, False])
    path = config.output_dir / "patient_level_90d_feature_importance_comparison.csv"
    importance_df.to_csv(path, index=False, encoding="utf-8-sig")

    plot_df = importance_df.groupby("model", group_keys=False).head(20)
    grid = sns.catplot(
        data=plot_df,
        kind="bar",
        y="feature",
        x="importance",
        col="model",
        sharex=False,
        sharey=False,
        color="#2f6f9f",
        height=7,
        aspect=0.9,
    )
    grid.fig.suptitle("Patient-Level 90-Day Feature Importance", y=1.02)
    plot_path = config.output_dir / "patient_level_90d_feature_importance_comparison.png"
    grid.fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(grid.fig)
    print(f"Saved feature importance: {path}")
    return importance_df


def choose_shap_model(metrics_df: pd.DataFrame, fitted: dict[str, Pipeline]) -> str | None:
    """Choose best tree model for SHAP using PR-AUC first."""
    for model_name in metrics_df["model"]:
        if model_name in {"random_forest", "xgboost"} and model_name in fitted:
            return model_name
    return None


def extract_binary_shap_values(shap_values):
    """Normalize SHAP values to positive-class array."""
    if isinstance(shap_values, list):
        return shap_values[1]
    if getattr(shap_values, "ndim", 0) == 3:
        return shap_values[:, :, 1]
    return shap_values


def expected_value_for_positive_class(explainer):
    """Return positive-class expected value when SHAP returns per-class values."""
    expected = explainer.expected_value
    if isinstance(expected, list):
        return expected[1]
    try:
        if len(expected) == 2:
            return expected[1]
    except TypeError:
        pass
    return expected


def run_shap(model_name: str, model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series, feature_columns: list[str], config: Config) -> None:
    """Run global and local SHAP explanations for the selected tree model."""
    if shap is None:
        print("SHAP is not installed. Skipping SHAP.")
        return

    sample_n = min(config.shap_sample_size, len(X_test))
    sample_indexes = []
    for target_value, target_index in y_test.groupby(y_test).groups.items():
        target_index = pd.Index(target_index)
        target_n = max(1, int(sample_n * len(target_index) / len(X_test)))
        sampled_index = target_index.to_series().sample(
            n=min(target_n, len(target_index)),
            random_state=config.random_state,
        )
        sample_indexes.extend(sampled_index.tolist())

    if len(sample_indexes) < sample_n:
        remaining = X_test.index.difference(sample_indexes)
        top_up = remaining.to_series().sample(
            n=min(sample_n - len(sample_indexes), len(remaining)),
            random_state=config.random_state,
        )
        sample_indexes.extend(top_up.tolist())

    X_sample_raw = X_test.loc[sample_indexes].copy()
    y_sample = y_test.loc[sample_indexes].copy()

    imputer = model.named_steps["imputer"]
    classifier = model.named_steps["classifier"]
    feature_names = transformed_feature_names(model, feature_columns)
    X_sample = pd.DataFrame(imputer.transform(X_sample_raw), columns=feature_names, index=X_sample_raw.index)

    explainer = shap.TreeExplainer(classifier)
    shap_values = extract_binary_shap_values(explainer.shap_values(X_sample))

    summary_path = config.output_dir / f"patient_level_90d_shap_summary_{model_name}.png"
    shap.summary_plot(shap_values, X_sample, show=False, max_display=25)
    plt.tight_layout()
    plt.savefig(summary_path, dpi=300, bbox_inches="tight")
    plt.close()

    bar_path = config.output_dir / f"patient_level_90d_shap_bar_{model_name}.png"
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False, max_display=25)
    plt.tight_layout()
    plt.savefig(bar_path, dpi=300, bbox_inches="tight")
    plt.close()

    pd.DataFrame({"feature": feature_names, "mean_abs_shap": abs(shap_values).mean(axis=0)}).sort_values(
        "mean_abs_shap", ascending=False
    ).to_csv(config.output_dir / f"patient_level_90d_shap_importance_{model_name}.csv", index=False, encoding="utf-8-sig")

    expected_value = expected_value_for_positive_class(explainer)
    for label, target_value in {"positive": 1, "negative": 0}.items():
        candidates = y_sample[y_sample == target_value].index
        if len(candidates) == 0:
            continue
        row_idx = candidates[0]
        pos = X_sample.index.get_loc(row_idx)
        explanation = shap.Explanation(
            values=shap_values[pos],
            base_values=expected_value,
            data=X_sample.iloc[pos],
            feature_names=list(X_sample.columns),
        )
        plt.figure(figsize=(10, 7))
        shap.plots.waterfall(explanation, max_display=20, show=False)
        local_path = config.output_dir / f"patient_level_90d_shap_local_{label}_{model_name}.png"
        plt.tight_layout()
        plt.savefig(local_path, dpi=300, bbox_inches="tight")
        plt.close()

    print(f"Saved SHAP outputs for: {model_name}")


def write_report(patient_df: pd.DataFrame, cv_summary: pd.DataFrame, holdout_metrics: pd.DataFrame, reports: dict, best_shap_model: str | None, config: Config) -> None:
    """Write a text report summarizing cohort, metrics, and model selection."""
    path = config.output_dir / "patient_level_90d_model_report.txt"
    with path.open("w", encoding="utf-8") as f:
        f.write("Patient-Level 90-Day Stroke Prediction Report\n")
        f.write("=============================================\n\n")
        f.write("Target: stroke within 90 days after index date based on PrincipleDiagnosis I60-I69*\n")
        f.write(f"Rows: {len(patient_df):,}\n")
        f.write(f"Positive: {int(patient_df['stroke_3m'].sum()):,}\n")
        f.write(f"Negative: {int((patient_df['stroke_3m'] == 0).sum()):,}\n")
        f.write(f"Prevalence: {patient_df['stroke_3m'].mean() * 100:.2f}%\n")
        f.write(f"Best SHAP model: {best_shap_model}\n\n")
        f.write("CV Summary\n----------\n")
        f.write(cv_summary.to_string(index=False))
        f.write("\n\nHoldout Metrics\n---------------\n")
        f.write(holdout_metrics.to_string(index=False))
        f.write("\n\n")
        for model_name, detail in reports.items():
            f.write(f"Confusion Matrix: {model_name}\n")
            f.write(str(detail["confusion_matrix"]))
            f.write("\n\n")
            f.write(detail["classification_report"])
            f.write("\n\n")
    print(f"Saved report: {path}")


def main() -> None:
    raw_df = load_raw_data(CONFIG)
    patient_df = build_patient_level_dataset(raw_df, CONFIG)

    feature_columns = get_feature_columns(patient_df)
    X = patient_df[feature_columns]
    y = patient_df["stroke_3m"]

    if y.nunique() < 2:
        raise ValueError("The patient-level cohort has only one class. Cannot train classifiers.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=CONFIG.test_size,
        stratify=y,
        random_state=CONFIG.random_state,
    )

    models = make_models(y, CONFIG)
    cv_summary = run_cv(models, X, y, CONFIG)

    holdout_models = make_models(y_train, CONFIG)
    fitted, holdout_metrics, reports = train_holdout(holdout_models, X_train, X_test, y_train, y_test, CONFIG)
    export_feature_importance(fitted, feature_columns, CONFIG)

    shap_model = choose_shap_model(holdout_metrics, fitted)
    if shap_model is not None:
        run_shap(shap_model, fitted[shap_model], X_test, y_test, feature_columns, CONFIG)

    write_report(patient_df, cv_summary, holdout_metrics, reports, shap_model, CONFIG)


if __name__ == "__main__":
    main()
