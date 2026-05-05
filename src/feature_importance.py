from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None

from modeling import Config as ModelingConfig
from modeling import get_feature_columns, load_feature_table, make_models, split_patient_level_data


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore", category=UserWarning)
sns.set_theme(style="whitegrid")


@dataclass(frozen=True)
class Config:
    feature_table_path: Path = Path("data/processed/patient_level_90d_stroke.csv")
    output_dir: Path = Path("output/model_output")
    target_column: str = "stroke_3m"
    random_state: int = 42
    test_size: float = 0.25
    shap_sample_size: int = 1000
    top_n: int = 25


def transformed_feature_names(model, original_feature_names: list[str]) -> list[str]:
    imputer = model.named_steps["imputer"]
    return list(imputer.get_feature_names_out(original_feature_names))


def transformed_matrix(model, X: pd.DataFrame, original_feature_names: list[str]) -> pd.DataFrame:
    imputer = model.named_steps["imputer"]
    feature_names = transformed_feature_names(model, original_feature_names)
    return pd.DataFrame(imputer.transform(X), columns=feature_names, index=X.index)


def train_models(X_train: pd.DataFrame, y_train: pd.Series, config: Config):
    modeling_config = ModelingConfig(
        feature_table_path=config.feature_table_path,
        output_dir=config.output_dir,
        target_column=config.target_column,
        random_state=config.random_state,
        test_size=config.test_size,
    )
    models = make_models(y_train, modeling_config)
    fitted = {}
    for model_name, model in models.items():
        print(f"Training model for importance: {model_name}")
        model.fit(X_train, y_train)
        fitted[model_name] = model
    return fitted


def export_tree_importance(
    fitted_models: dict,
    feature_columns: list[str],
    config: Config,
) -> pd.DataFrame:
    rows = []
    for model_name, model in fitted_models.items():
        classifier = model.named_steps["classifier"]
        if not hasattr(classifier, "feature_importances_"):
            continue

        names = transformed_feature_names(model, feature_columns)
        rows.extend(
            {
                "model": model_name,
                "feature": feature,
                "importance": float(importance),
                "importance_type": "model_native_tree",
            }
            for feature, importance in zip(names, classifier.feature_importances_, strict=False)
        )

    if not rows:
        raise ValueError("No fitted tree-based model exposes feature_importances_.")

    importance_df = (
        pd.DataFrame(rows)
        .sort_values(["model", "importance"], ascending=[True, False])
        .reset_index(drop=True)
    )
    output_path = config.output_dir / "patient_level_90d_feature_importance_comparison.csv"
    importance_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved tree importance table: {output_path}")
    plot_importance_comparison(importance_df, config)
    return importance_df


def plot_importance_comparison(importance_df: pd.DataFrame, config: Config) -> None:
    top_frames = []
    for model_name, group in importance_df.groupby("model"):
        top_frames.append(group.nlargest(config.top_n, "importance"))
    plot_df = pd.concat(top_frames, ignore_index=True)

    grid = sns.catplot(
        data=plot_df,
        kind="bar",
        y="feature",
        x="importance",
        col="model",
        sharex=False,
        sharey=False,
        color="#2f6f9f",
        height=8,
        aspect=0.85,
    )
    grid.set_axis_labels("Model-native importance", "Feature")
    grid.set_titles("{col_name}")
    grid.fig.suptitle("Patient-Level 90-Day Stroke Feature Importance", y=1.02)

    output_path = config.output_dir / "patient_level_90d_feature_importance_comparison.png"
    grid.fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(grid.fig)
    print(f"Saved tree importance plot: {output_path}")


def select_shap_model(fitted_models: dict, holdout_metrics_path: Path) -> str:
    if holdout_metrics_path.exists():
        metrics = pd.read_csv(holdout_metrics_path)
        if {"model", "pr_auc"}.issubset(metrics.columns):
            ranked = metrics[metrics["model"].isin(fitted_models)].sort_values(
                ["pr_auc", "roc_auc"],
                ascending=False,
            )
            if not ranked.empty:
                return str(ranked.iloc[0]["model"])

    for preferred_model in ("xgboost", "random_forest"):
        if preferred_model in fitted_models:
            return preferred_model
    return next(iter(fitted_models))


def stratified_shap_sample(
    X: pd.DataFrame,
    y: pd.Series,
    sample_size: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    if len(X) <= sample_size:
        return X.copy(), y.copy()

    sample_indices = []
    for target_value, target_index in y.groupby(y).groups.items():
        class_count = len(target_index)
        n = max(1, round(sample_size * class_count / len(y)))
        sampled = pd.Index(target_index).to_series().sample(
            n=min(n, class_count),
            random_state=random_state + int(target_value),
        )
        sample_indices.extend(sampled.tolist())

    if len(sample_indices) < sample_size:
        remaining = X.index.difference(sample_indices)
        extra = remaining.to_series().sample(
            n=min(sample_size - len(sample_indices), len(remaining)),
            random_state=random_state,
        )
        sample_indices.extend(extra.tolist())

    sample_indices = sample_indices[:sample_size]
    return X.loc[sample_indices].copy(), y.loc[sample_indices].copy()


def positive_class_shap_values(shap_values) -> np.ndarray:
    if isinstance(shap_values, list):
        return np.asarray(shap_values[1])
    values = np.asarray(shap_values)
    if values.ndim == 3:
        return values[:, :, 1]
    return values


def positive_expected_value(explainer):
    expected_value = explainer.expected_value
    if isinstance(expected_value, list):
        return expected_value[1]
    values = np.asarray(expected_value)
    if values.ndim > 0 and len(values) == 2:
        return values[1]
    return expected_value


def run_shap_analysis(
    model_name: str,
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_columns: list[str],
    config: Config,
) -> dict[str, str]:
    if shap is None:
        print("SHAP is not installed. Skipping SHAP outputs.")
        return {}

    classifier = model.named_steps["classifier"]
    if not hasattr(classifier, "feature_importances_"):
        print(f"{model_name} is not tree-based. Skipping SHAP outputs.")
        return {}

    print(f"Running SHAP analysis: {model_name}")
    shap_X_raw, shap_y = stratified_shap_sample(
        X_test,
        y_test,
        sample_size=config.shap_sample_size,
        random_state=config.random_state,
    )
    shap_X = transformed_matrix(model, shap_X_raw, feature_columns)
    explainer = shap.TreeExplainer(classifier)
    shap_values = positive_class_shap_values(explainer.shap_values(shap_X))

    outputs = {
        "summary_plot": str(config.output_dir / f"patient_level_90d_shap_summary_{model_name}.png"),
        "bar_plot": str(config.output_dir / f"patient_level_90d_shap_bar_{model_name}.png"),
        "importance_csv": str(config.output_dir / f"patient_level_90d_shap_importance_{model_name}.csv"),
        "local_positive_plot": str(config.output_dir / f"patient_level_90d_shap_local_positive_{model_name}.png"),
        "local_negative_plot": str(config.output_dir / f"patient_level_90d_shap_local_negative_{model_name}.png"),
    }

    shap.summary_plot(shap_values, shap_X, show=False, max_display=config.top_n)
    plt.title(f"SHAP Summary: {model_name}")
    plt.tight_layout()
    plt.savefig(outputs["summary_plot"], dpi=300, bbox_inches="tight")
    plt.close()

    shap.summary_plot(shap_values, shap_X, plot_type="bar", show=False, max_display=config.top_n)
    plt.title(f"SHAP Mean Absolute Importance: {model_name}")
    plt.tight_layout()
    plt.savefig(outputs["bar_plot"], dpi=300, bbox_inches="tight")
    plt.close()

    shap_importance = (
        pd.DataFrame(
            {
                "model": model_name,
                "feature": shap_X.columns,
                "mean_abs_shap": np.abs(shap_values).mean(axis=0),
                "importance_type": "mean_absolute_shap",
            }
        )
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    shap_importance.to_csv(outputs["importance_csv"], index=False, encoding="utf-8-sig")

    save_local_shap_plot(
        output_path=Path(outputs["local_positive_plot"]),
        label="positive",
        explainer=explainer,
        shap_values=shap_values,
        shap_X=shap_X,
        shap_y=shap_y,
    )
    save_local_shap_plot(
        output_path=Path(outputs["local_negative_plot"]),
        label="negative",
        explainer=explainer,
        shap_values=shap_values,
        shap_X=shap_X,
        shap_y=shap_y,
    )
    print(f"Saved SHAP outputs for {model_name}")
    return outputs


def save_local_shap_plot(
    output_path: Path,
    label: str,
    explainer,
    shap_values: np.ndarray,
    shap_X: pd.DataFrame,
    shap_y: pd.Series,
) -> None:
    target_value = 1 if label == "positive" else 0
    candidate_index = shap_y[shap_y == target_value].index
    if len(candidate_index) == 0:
        print(f"No {label} cases in SHAP sample. Skipping local plot.")
        return

    row_index = candidate_index[0]
    row_position = shap_X.index.get_loc(row_index)
    explanation = shap.Explanation(
        values=shap_values[row_position],
        base_values=positive_expected_value(explainer),
        data=shap_X.iloc[row_position],
        feature_names=list(shap_X.columns),
    )
    plt.figure(figsize=(10, 7))
    shap.plots.waterfall(explanation, max_display=20, show=False)
    plt.title(f"Local SHAP Explanation ({label} patient)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def write_interpretation_report(
    patient_df: pd.DataFrame,
    importance_df: pd.DataFrame,
    shap_outputs: dict[str, str],
    shap_model_name: str,
    config: Config,
) -> dict[str, object]:
    top_by_model = {
        model_name: group.nlargest(10, "importance")["feature"].tolist()
        for model_name, group in importance_df.groupby("model")
    }
    payload: dict[str, object] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "feature_table_path": str(config.feature_table_path),
        "target": config.target_column,
        "unit_of_analysis": "patient",
        "patient_rows": int(len(patient_df)),
        "positive_patients": int(patient_df[config.target_column].sum()),
        "negative_patients": int((patient_df[config.target_column] == 0).sum()),
        "prevalence_percent": round(float(patient_df[config.target_column].mean() * 100), 2),
        "shap_model": shap_model_name,
        "top_features_by_model": top_by_model,
        "outputs": {
            "tree_importance_csv": str(config.output_dir / "patient_level_90d_feature_importance_comparison.csv"),
            "tree_importance_plot": str(config.output_dir / "patient_level_90d_feature_importance_comparison.png"),
            **shap_outputs,
        },
        "interpretation_notes": [
            "Importance explains model behavior for patient-level stroke_3m prediction, not causal effects.",
            "Model-native tree importance can favor continuous or high-cardinality variables.",
            "Missing indicator features describe data availability patterns, not direct lab values.",
            "Local SHAP plots explain individual sampled patients and should not be generalized to the full cohort.",
        ],
    }

    json_path = config.output_dir / "patient_level_90d_feature_importance_report.json"
    txt_path = config.output_dir / "patient_level_90d_feature_importance_report.txt"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    with txt_path.open("w", encoding="utf-8") as file:
        file.write("Patient-Level 90-Day Stroke Feature Importance Report\n")
        file.write("=====================================================\n\n")
        file.write(f"Target: {config.target_column}\n")
        file.write("Unit of analysis: patient\n")
        file.write(f"Rows: {payload['patient_rows']:,}\n")
        file.write(f"Positive patients: {payload['positive_patients']:,}\n")
        file.write(f"Prevalence: {payload['prevalence_percent']}%\n")
        file.write(f"SHAP model: {shap_model_name}\n\n")
        for model_name, features in top_by_model.items():
            file.write(f"Top features: {model_name}\n")
            for rank, feature in enumerate(features, start=1):
                file.write(f"{rank}. {feature}\n")
            file.write("\n")
        file.write("Interpretation Notes\n")
        file.write("--------------------\n")
        for note in payload["interpretation_notes"]:
            file.write(f"- {note}\n")

    print(f"Saved interpretation report: {txt_path}")
    return payload


def run(config: Config) -> dict[str, object]:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    modeling_config = ModelingConfig(
        feature_table_path=config.feature_table_path,
        output_dir=config.output_dir,
        target_column=config.target_column,
        random_state=config.random_state,
        test_size=config.test_size,
    )
    patient_df = load_feature_table(modeling_config)
    feature_columns = get_feature_columns(patient_df, modeling_config)
    X = patient_df[feature_columns]
    y = patient_df[config.target_column]
    hn = patient_df["hn"]

    X_train, X_test, y_train, y_test, _, _ = split_patient_level_data(X, y, hn, modeling_config)
    fitted_models = train_models(X_train, y_train, config)
    importance_df = export_tree_importance(fitted_models, feature_columns, config)

    shap_model_name = select_shap_model(
        fitted_models,
        config.output_dir / "patient_level_90d_holdout_metrics.csv",
    )
    shap_outputs = run_shap_analysis(
        model_name=shap_model_name,
        model=fitted_models[shap_model_name],
        X_test=X_test,
        y_test=y_test,
        feature_columns=feature_columns,
        config=config,
    )
    return write_interpretation_report(patient_df, importance_df, shap_outputs, shap_model_name, config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Explain patient-level 90-day stroke prediction models.")
    parser.add_argument("--feature-table", default=str(Config.feature_table_path), help="Patient-level feature table CSV.")
    parser.add_argument("--output-dir", default=str(Config.output_dir), help="Feature importance output directory.")
    parser.add_argument("--test-size", type=float, default=Config.test_size, help="Holdout test fraction.")
    parser.add_argument("--shap-sample-size", type=int, default=Config.shap_sample_size, help="Rows sampled from holdout set for SHAP.")
    parser.add_argument("--top-n", type=int, default=Config.top_n, help="Number of top features to show in plots.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        feature_table_path=Path(args.feature_table),
        output_dir=Path(args.output_dir),
        test_size=args.test_size,
        shap_sample_size=args.shap_sample_size,
        top_n=args.top_n,
    )
    payload = run(config)
    print("Feature importance completed")
    print(f"Target: {payload['target']}")
    print(f"SHAP model: {payload['shap_model']}")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
