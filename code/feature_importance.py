# =========================
# Stroke Prediction Feature Importance
# =========================
#
# สคริปต์นี้ใช้สำหรับงานทำนาย/จำแนกผู้ป่วย Stroke จากข้อมูลผู้ป่วยแบบ tabular
# โดยเน้น 5 เรื่องหลัก:
#   1) สร้าง target stroke_flag จากรหัส ICD-10 ในคอลัมน์ PrincipleDiagnosis
#   2) train โมเดล RandomForest และ XGBoost เพื่อเปรียบเทียบผล
#   3) ใช้ Stratified K-Fold Cross Validation เพื่อดูความเสถียรของ metrics
#   4) export feature importance ของแต่ละโมเดลเพื่อดู feature ที่สำคัญ
#   5) ใช้ SHAP อธิบายโมเดลทั้งแบบ global และ local
#
# นิยาม target:
#   stroke_flag = 1 เมื่อ PrincipleDiagnosis เป็น ICD-10 ช่วง I60-I69*
#   ตัวอย่างรหัสที่นับเป็น stroke: I60, I639, I64, I694, I699
#   หมายเหตุ: ใช้เฉพาะ PrincipleDiagnosis ตาม requirement ล่าสุด
#
# output ทั้งหมดจะถูกบันทึกไว้ที่:
#   output/feature_importance_output/

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import warnings

import matplotlib

# ใช้ backend แบบไม่เปิดหน้าต่างกราฟ เพื่อให้รันบน server/headless environment ได้
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

try:
    import shap
except ImportError:  # pragma: no cover - handled at runtime for portability
    # ถ้าเครื่องปลายทางยังไม่ได้ติดตั้ง shap สคริปต์จะยังรันส่วน modeling ได้
    # และจะ skip เฉพาะขั้นตอน SHAP analysis
    shap = None

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover - handled at runtime for portability
    # ถ้ายังไม่มี xgboost จะยังรัน RandomForest ได้ตามเดิม
    XGBClassifier = None


if hasattr(sys.stdout, "reconfigure"):
    # แก้ปัญหา Windows console encode ภาษาไทยไม่ได้ในบางเครื่อง
    sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore", category=UserWarning)
sns.set_theme(style="whitegrid")


@dataclass(frozen=True)
class Config:
    """รวมค่าตั้งต้นของ workflow ไว้ในที่เดียว เพื่อแก้ง่ายและลด hard-code กระจายทั้งไฟล์."""

    # ไฟล์ Excel ต้นทาง
    data_path: Path = Path("patients_with_tc_hdl_ratio_with_drugflag.xlsx")

    # โฟลเดอร์ output เฉพาะงาน feature importance/modeling
    output_dir: Path = Path("output") / "feature_importance_output"

    # seed เพื่อให้ train/test split, sampling และ model reproducible
    random_state: int = 42

    # holdout test set 25% ของข้อมูลทั้งหมด
    test_size: float = 0.25

    # ใช้ 3 folds เพื่อ balance ระหว่างความเสถียรกับเวลาในการรันบนข้อมูลใหญ่
    cv_splits: int = 3

    # จำกัดจำนวน record สำหรับ cross-validation เพื่อรองรับ dataset ใหญ่
    # final holdout training ยังใช้ train split จากข้อมูลเต็ม ไม่ได้ลดขนาด
    cv_max_rows: int = 60000

    # จำกัดจำนวน sample สำหรับ SHAP เพราะ SHAP บน tree model กับข้อมูลใหญ่ใช้เวลาสูง
    shap_sample_size: int = 1000

    # reserved ไว้สำหรับอนาคต หากต้องการเลือก local case ตาม rank แทน case แรก
    local_positive_rank: int = 0
    local_negative_rank: int = 0


CONFIG = Config()
CONFIG.output_dir.mkdir(parents=True, exist_ok=True)

# pattern นี้รับรหัส I60-I69 ที่อาจเขียนแบบไม่มีจุด เช่น I639, I694, I699
STROKE_PATTERN = re.compile(r"^I6[0-9][0-9A-Z]*$", re.IGNORECASE)

# รายการ feature ที่อนุญาตให้โมเดลใช้
# ไม่ใส่ PrincipleDiagnosis, ComorbidityDiagnosis, ยาที่ได้รับ, ตำบล หรือ text fields
# เพราะ PrincipleDiagnosis ใช้สร้าง target และ text/diagnosis อาจทำให้เกิด data leakage
FEATURE_COLUMNS = [
    "sex",
    "age",
    "height",
    "bw",
    "bmi",
    "smoke",
    "drinking",
    "bps",
    "bpd",
    "HDL",
    "LDL",
    "Triglyceride",
    "Cholesterol",
    "AF",
    "FBS",
    "eGFR",
    "Creatinine",
    "heart_disease",
    "hypertension",
    "diabetes",
    "Statin",
    "Gemfibrozil",
    "TC:HDL_ratio",
    "Antihypertensive_flag",
    "visit_year",
    "visit_month",
]


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """สร้าง feature จากวันที่เข้ารับบริการ เช่น ปีและเดือนของ visit."""
    df = df.copy()

    # errors="coerce" จะเปลี่ยนวันที่ที่ parse ไม่ได้ให้เป็น NaT แทนการ throw error
    df["vstdate"] = pd.to_datetime(df["vstdate"], errors="coerce")
    df["visit_year"] = df["vstdate"].dt.year
    df["visit_month"] = df["vstdate"].dt.month
    return df


def build_stroke_flag(df: pd.DataFrame) -> pd.Series:
    """สร้าง target stroke_flag จาก PrincipleDiagnosis เท่านั้น."""

    # แปลงเป็น string, strip ช่องว่าง, เติมค่าว่างแทน missing เพื่อให้ regex ทำงานปลอดภัย
    principle_diagnosis = df["PrincipleDiagnosis"].astype("string").str.strip().fillna("")

    # ถ้ารหัสตรง I60-I69* ให้เป็น 1, ถ้าไม่ตรงให้เป็น 0
    return principle_diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def load_dataset(config: Config) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, list[str]]:
    """โหลดข้อมูล, สร้าง feature เพิ่ม, สร้าง target, แล้วคืน X/y สำหรับ train model."""
    print(f"Loading data: {config.data_path}")
    df = pd.read_excel(config.data_path)
    df = add_date_features(df)
    df["stroke_flag"] = build_stroke_flag(df)

    # เผื่อบาง dataset ไม่มีบางคอลัมน์ จะใช้เฉพาะ feature ที่พบจริง
    available_features = [col for col in FEATURE_COLUMNS if col in df.columns]
    X = df[available_features].copy()
    y = df["stroke_flag"].copy()

    # summary นี้ช่วยตรวจ sanity ของ target ทุกครั้งที่รัน
    print("Dataset shape:", df.shape)
    print("Feature count:", len(available_features))
    print("Stroke records:", int(y.sum()))
    print("Non-stroke records:", int((y == 0).sum()))
    print("Stroke prevalence:", f"{y.mean() * 100:.2f}%")
    return df, X, y, available_features


def make_preprocessor() -> SimpleImputer:
    """สร้าง preprocessor สำหรับจัดการ missing values."""

    # ใช้ median เพราะทนต่อ outliers กว่า mean ในข้อมูล clinical/lab
    # add_indicator=True เพิ่ม binary column บอกว่า feature เดิมหายไปหรือไม่
    # ซึ่งมีประโยชน์เมื่อ pattern ของ missing เองมีสัญญาณทางคลินิก
    return SimpleImputer(strategy="median", add_indicator=True)


def get_rf_model(config: Config) -> RandomForestClassifier:
    """
    สร้าง RandomForest model

    เหตุผลของ parameter หลัก:
    - n_estimators=200: จำนวนต้นไม้พอให้ผลนิ่ง แต่ยังรันได้ในเวลารับได้
    - class_weight="balanced_subsample": ช่วย class imbalance ในแต่ละ bootstrap sample
    - min_samples_leaf=5: ลด over-smoothing จากค่าเดิม 20 แต่ยังกัน leaf ที่เล็กเกินไป
    - min_samples_split=10: ลดการแตก node ที่เล็กและ noisy
    - max_features="sqrt": ลด correlation ระหว่างต้นไม้ และเป็น default ที่ดีสำหรับ classification
    """
    return RandomForestClassifier(
        n_estimators=200,
        random_state=config.random_state,
        n_jobs=1,  # ใช้ 1 เพื่อเลี่ยง permission/thread issue บน Windows environment นี้
        class_weight="balanced_subsample",
        min_samples_leaf=5,
        min_samples_split=10,
        max_features="sqrt",
    )


def get_xgb_model(y: pd.Series, config: Config):
    """สร้าง XGBoost model โดยคำนวณ scale_pos_weight จากสัดส่วน class imbalance."""
    if XGBClassifier is None:
        return None

    # scale_pos_weight = จำนวน negative / จำนวน positive
    # ช่วยให้ XGBoost ให้ weight กับ stroke class มากขึ้น
    positive_count = int(y.sum())
    negative_count = int((y == 0).sum())
    scale_pos_weight = negative_count / max(positive_count, 1)

    return XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=10,
        reg_lambda=2.0,
        objective="binary:logistic",
        eval_metric="auc",
        tree_method="hist",
        random_state=config.random_state,
        n_jobs=1,
        scale_pos_weight=scale_pos_weight,
    )


def build_models(y: pd.Series, config: Config) -> dict[str, Pipeline]:
    """รวมโมเดลทั้งหมดเป็น sklearn Pipeline เพื่อให้ preprocessing อยู่ใน CV อย่างถูกต้อง."""

    # Pipeline สำคัญมาก เพราะ imputer จะ fit เฉพาะ train fold เท่านั้น
    # ช่วยป้องกัน data leakage จาก validation/test fold
    models = {
        "random_forest": Pipeline(
            steps=[
                ("imputer", make_preprocessor()),
                ("classifier", get_rf_model(config)),
            ]
        )
    }

    xgb_model = get_xgb_model(y, config)
    if xgb_model is not None:
        models["xgboost"] = Pipeline(
            steps=[
                ("imputer", make_preprocessor()),
                ("classifier", xgb_model),
            ]
        )
    else:
        print("XGBoost is not installed. Skipping xgboost model.")

    return models


def predict_scores(model: Pipeline, X: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """คืนค่า class prediction และ probability ของ positive class (stroke=1)."""
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]
    return y_pred, y_proba


def compute_metrics(y_true: pd.Series, y_pred, y_proba) -> dict[str, float]:
    """คำนวณ metrics หลักสำหรับ binary classification ที่ class imbalance."""

    # ROC-AUC ใช้ probability จึงวัดการจัดอันดับความเสี่ยง
    # precision/recall/f1 สำคัญกว่า accuracy ในกรณี stroke prevalence ต่ำ
    return {
        "roc_auc": roc_auc_score(y_true, y_proba),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def run_cross_validation(
    models: dict[str, Pipeline],
    X: pd.DataFrame,
    y: pd.Series,
    config: Config,
) -> pd.DataFrame:
    """รัน Stratified K-Fold CV และบันทึก metrics ราย fold."""

    # Dataset มีมากกว่า 2 แสนแถว การทำ CV เต็มทุกแถวกับหลายโมเดลใช้เวลาสูงมาก
    # จึงใช้ stratified sample สำหรับ CV เพื่อให้สัดส่วน stroke/non-stroke ยังใกล้เดิม
    # ส่วน final holdout training ยังใช้ข้อมูล train split จาก dataset เต็ม
    if len(X) > config.cv_max_rows:
        cv_index = (
            pd.DataFrame({"target": y})
            .groupby("target", group_keys=False)
            .apply(
                lambda part: part.sample(
                    n=max(1, int(config.cv_max_rows * len(part) / len(y))),
                    random_state=config.random_state,
                )
            )
            .index
        )
        X = X.loc[cv_index].copy()
        y = y.loc[cv_index].copy()
        print(
            f"Using stratified CV sample: {len(X):,} rows "
            f"from {len(cv_index):,} sampled indexes."
        )

    cv = StratifiedKFold(
        n_splits=config.cv_splits,
        shuffle=True,
        random_state=config.random_state,
    )
    rows = []

    for model_name, model in models.items():
        print(f"Running {config.cv_splits}-fold CV: {model_name}")
        for fold, (train_idx, valid_idx) in enumerate(cv.split(X, y), start=1):
            # แยก train/validation ของ fold นี้
            X_train_fold = X.iloc[train_idx]
            X_valid_fold = X.iloc[valid_idx]
            y_train_fold = y.iloc[train_idx]
            y_valid_fold = y.iloc[valid_idx]

            # fit pipeline ใหม่ในแต่ละ fold เพื่อให้ imputer/model ไม่เห็น validation fold
            model.fit(X_train_fold, y_train_fold)
            y_pred, y_proba = predict_scores(model, X_valid_fold)
            metrics = compute_metrics(y_valid_fold, y_pred, y_proba)
            rows.append({"model": model_name, "fold": fold, **metrics})
            print(
                f"  fold={fold} auc={metrics['roc_auc']:.4f} "
                f"recall={metrics['recall']:.4f} precision={metrics['precision']:.4f}"
            )

    cv_df = pd.DataFrame(rows)
    cv_path = CONFIG.output_dir / "model_cv_metrics.csv"
    cv_df.to_csv(cv_path, index=False, encoding="utf-8-sig")
    print(f"Saved CV metrics: {cv_path}")
    return cv_df


def summarize_cv(cv_df: pd.DataFrame) -> pd.DataFrame:
    """สรุปค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของ CV metrics แยกตามโมเดล."""
    metric_columns = ["roc_auc", "accuracy", "precision", "recall", "f1"]
    summary = (
        cv_df.groupby("model")[metric_columns]
        .agg(["mean", "std"])
        .reset_index()
    )
    summary.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col for col in summary.columns
    ]
    summary_path = CONFIG.output_dir / "model_cv_metrics_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"Saved CV summary: {summary_path}")
    return summary


def train_holdout_models(
    models: dict[str, Pipeline],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict[str, Pipeline], pd.DataFrame, dict[str, dict]]:
    """train โมเดลบน train split จากข้อมูลเต็ม และประเมินบน holdout test set."""
    fitted_models = {}
    metric_rows = []
    evaluation_details = {}

    for model_name, model in models.items():
        print(f"Training holdout model: {model_name}")

        # ขั้นตอนนี้คือ final model comparison หลังจากดู CV แล้ว
        model.fit(X_train, y_train)
        y_pred, y_proba = predict_scores(model, X_test)
        metrics = compute_metrics(y_test, y_pred, y_proba)

        fitted_models[model_name] = model
        metric_rows.append({"model": model_name, **metrics})
        evaluation_details[model_name] = {
            "y_pred": y_pred,
            "y_proba": y_proba,
            "confusion_matrix": confusion_matrix(y_test, y_pred),
            "classification_report": classification_report(y_test, y_pred, digits=4),
        }
        print(f"  holdout auc={metrics['roc_auc']:.4f} f1={metrics['f1']:.4f}")

    metrics_df = pd.DataFrame(metric_rows).sort_values("roc_auc", ascending=False)
    metrics_path = CONFIG.output_dir / "model_holdout_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    print(f"Saved holdout metrics: {metrics_path}")
    return fitted_models, metrics_df, evaluation_details


def get_transformed_feature_names(model: Pipeline, feature_columns: list[str]) -> list[str]:
    """คืนชื่อ feature หลังผ่าน imputer รวมถึง missing indicator columns."""
    imputer = model.named_steps["imputer"]
    return list(imputer.get_feature_names_out(feature_columns))


def get_model_importance(
    model_name: str,
    model: Pipeline,
    feature_columns: list[str],
) -> pd.DataFrame:
    """ดึง feature_importances_ จาก tree-based classifier."""
    classifier = model.named_steps["classifier"]
    feature_names = get_transformed_feature_names(model, feature_columns)

    if not hasattr(classifier, "feature_importances_"):
        raise ValueError(f"{model_name} does not expose feature_importances_.")

    return (
        pd.DataFrame(
            {
                "model": model_name,
                "feature": feature_names,
                "importance": classifier.feature_importances_,
            }
        )
        .sort_values(["model", "importance"], ascending=[True, False])
        .reset_index(drop=True)
    )


def export_feature_importance(
    fitted_models: dict[str, Pipeline],
    feature_columns: list[str],
) -> pd.DataFrame:
    """บันทึก feature importance ของแต่ละโมเดล และสร้างกราฟเปรียบเทียบ."""
    importance_frames = [
        get_model_importance(model_name, model, feature_columns)
        for model_name, model in fitted_models.items()
    ]
    importance_df = pd.concat(importance_frames, ignore_index=True)

    comparison_path = CONFIG.output_dir / "feature_importance_model_comparison.csv"
    importance_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    print(f"Saved importance comparison: {comparison_path}")

    # คง output ชื่อเดิมของ RandomForest ไว้ เพื่อไม่ทำลาย workflow เดิม
    if "random_forest" in fitted_models:
        rf_importance = (
            importance_df[importance_df["model"] == "random_forest"]
            .drop(columns=["model"])
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        rf_path = CONFIG.output_dir / "feature_importance_stroke.csv"
        rf_importance.to_csv(rf_path, index=False, encoding="utf-8-sig")
        print(f"Saved RandomForest importance table: {rf_path}")
        save_single_model_importance_plot(
            rf_importance,
            CONFIG.output_dir / "feature_importance_stroke.png",
            "RandomForest Top 20 Feature Importance",
        )

    save_feature_importance_comparison_plot(importance_df)
    return importance_df


def save_single_model_importance_plot(
    importance_df: pd.DataFrame,
    output_path: Path,
    title: str,
    top_n: int = 20,
) -> None:
    """บันทึกกราฟ bar chart แนวนอนของ top feature importance สำหรับโมเดลเดียว."""
    top_features = importance_df.head(top_n).copy()
    plt.figure(figsize=(10, 8))
    sns.barplot(data=top_features, y="feature", x="importance", color="#2f6f9f")
    plt.title(title)
    plt.xlabel("Model-native importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {output_path}")


def save_feature_importance_comparison_plot(
    importance_df: pd.DataFrame,
    top_n_per_model: int = 15,
) -> None:
    """บันทึกกราฟเปรียบเทียบ top feature importance ระหว่างโมเดล."""
    top_frames = []
    for model_name, group in importance_df.groupby("model"):
        top_frames.append(group.sort_values("importance", ascending=False).head(top_n_per_model))
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
        height=7,
        aspect=0.9,
    )
    grid.set_axis_labels("Model-native importance", "Feature")
    grid.set_titles("{col_name}")
    grid.fig.suptitle("Feature Importance Comparison by Model", y=1.02)

    output_path = CONFIG.output_dir / "feature_importance_model_comparison.png"
    grid.fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(grid.fig)
    print(f"Saved plot: {output_path}")


def select_best_model(metrics_df: pd.DataFrame) -> str:
    """เลือกโมเดลที่ดีที่สุดจาก holdout ROC-AUC เพื่อใช้ทำ SHAP."""
    return metrics_df.sort_values("roc_auc", ascending=False).iloc[0]["model"]


def sample_for_shap(
    X: pd.DataFrame,
    y: pd.Series,
    sample_size: int,
    random_state: int,
) -> pd.DataFrame:
    """สุ่มตัวอย่างแบบ stratified สำหรับ SHAP เพื่อจำกัดเวลาและ memory."""
    if len(X) <= sample_size:
        return X.copy()

    sample_idx = (
        pd.DataFrame({"target": y})
        .groupby("target", group_keys=False)
        .apply(
            lambda part: part.sample(
                n=max(1, int(sample_size * len(part) / len(y))),
                random_state=random_state,
            )
        )
        .index
    )

    # เติม sample เพิ่ม ถ้าการปัดเศษตามสัดส่วนทำให้จำนวนตัวอย่างน้อยกว่าที่ต้องการ
    if len(sample_idx) < sample_size:
        remaining = X.index.difference(sample_idx)
        extra = remaining.to_series().sample(
            n=min(sample_size - len(sample_idx), len(remaining)),
            random_state=random_state,
        )
        sample_idx = sample_idx.append(pd.Index(extra))

    return X.loc[sample_idx].copy()


def extract_binary_shap_values(shap_values):
    """
    ปรับรูปแบบ SHAP values ให้เหลือเฉพาะ positive class

    SHAP TreeExplainer ในแต่ละ version/model อาจคืนค่าไม่เหมือนกัน:
      - list[class0, class1]
      - array(n_samples, n_features)
      - array(n_samples, n_features, n_classes)
    """
    if isinstance(shap_values, list):
        return shap_values[1]
    if getattr(shap_values, "ndim", 0) == 3:
        return shap_values[:, :, 1]
    return shap_values


def run_shap_analysis(
    model_name: str,
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_columns: list[str],
    config: Config,
) -> None:
    """รัน SHAP ทั้ง global summary และ local explanation สำหรับ best model."""
    if shap is None:
        print("SHAP is not installed. Skipping SHAP analysis.")
        return

    print(f"Running SHAP analysis for best model: {model_name}")

    # ใช้เฉพาะ sample ของ test set เพื่อให้คำอธิบายสะท้อนข้อมูลที่โมเดลไม่เคยเห็น
    shap_X_raw = sample_for_shap(
        X_test,
        y_test,
        sample_size=config.shap_sample_size,
        random_state=config.random_state,
    )
    shap_y = y_test.loc[shap_X_raw.index]

    imputer = model.named_steps["imputer"]
    classifier = model.named_steps["classifier"]
    feature_names = get_transformed_feature_names(model, feature_columns)

    # SHAP ต้องใช้ matrix หลัง preprocessing ดังนั้นต้อง transform ด้วย imputer เดียวกับโมเดล
    shap_X = pd.DataFrame(
        imputer.transform(shap_X_raw),
        columns=feature_names,
        index=shap_X_raw.index,
    )

    explainer = shap.TreeExplainer(classifier)
    raw_shap_values = explainer.shap_values(shap_X)
    shap_values = extract_binary_shap_values(raw_shap_values)

    # SHAP summary plot: เห็นทั้งความสำคัญและทิศทางของ feature ต่อ prediction
    summary_path = config.output_dir / f"shap_summary_{model_name}.png"
    shap.summary_plot(shap_values, shap_X, show=False, max_display=25)
    plt.title(f"SHAP Summary: {model_name}")
    plt.tight_layout()
    plt.savefig(summary_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved SHAP summary: {summary_path}")

    # SHAP bar plot: ranking ของ mean absolute SHAP value
    bar_path = config.output_dir / f"shap_bar_{model_name}.png"
    shap.summary_plot(shap_values, shap_X, plot_type="bar", show=False, max_display=25)
    plt.title(f"SHAP Mean Absolute Importance: {model_name}")
    plt.tight_layout()
    plt.savefig(bar_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved SHAP bar plot: {bar_path}")

    # เก็บค่า mean_abs_shap เป็น CSV เพื่อเอาไปใช้ทำรายงาน/ตารางต่อได้
    shap_importance = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "mean_abs_shap": abs(shap_values).mean(axis=0),
            }
        )
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    shap_importance_path = config.output_dir / f"shap_importance_{model_name}.csv"
    shap_importance.to_csv(shap_importance_path, index=False, encoding="utf-8-sig")
    print(f"Saved SHAP importance table: {shap_importance_path}")

    save_local_shap_plots(
        model_name=model_name,
        explainer=explainer,
        shap_values=shap_values,
        shap_X=shap_X,
        shap_y=shap_y,
        config=config,
    )


def get_expected_value(explainer):
    """คืน expected value ของ positive class เมื่อ SHAP แยกค่าตาม class."""
    expected_value = explainer.expected_value
    if isinstance(expected_value, list):
        return expected_value[1]
    try:
        if len(expected_value) == 2:
            return expected_value[1]
    except TypeError:
        pass
    return expected_value


def save_local_shap_plots(
    model_name: str,
    explainer,
    shap_values,
    shap_X: pd.DataFrame,
    shap_y: pd.Series,
    config: Config,
) -> None:
    """บันทึก local waterfall plot สำหรับตัวอย่าง stroke และ non-stroke อย่างละ 1 record."""
    expected_value = get_expected_value(explainer)
    local_targets = {
        "positive": shap_y[shap_y == 1].index,
        "negative": shap_y[shap_y == 0].index,
    }

    for label, candidate_index in local_targets.items():
        if len(candidate_index) == 0:
            print(f"No {label} cases in SHAP sample. Skipping local SHAP plot.")
            continue

        # เลือก case แรกของแต่ละ class ใน SHAP sample
        # waterfall plot ช่วยตอบว่าฟีเจอร์ใดดัน prediction ขึ้น/ลงในราย record
        row_index = candidate_index[0]
        row_position = shap_X.index.get_loc(row_index)
        explanation = shap.Explanation(
            values=shap_values[row_position],
            base_values=expected_value,
            data=shap_X.iloc[row_position],
            feature_names=list(shap_X.columns),
        )

        plt.figure(figsize=(10, 7))
        shap.plots.waterfall(explanation, max_display=20, show=False)
        plt.title(f"Local SHAP Explanation ({label} case): {model_name}")
        output_path = config.output_dir / f"shap_local_{label}_{model_name}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Saved local SHAP plot: {output_path}")


def write_metrics_report(
    df: pd.DataFrame,
    y: pd.Series,
    feature_columns: list[str],
    cv_summary: pd.DataFrame,
    holdout_metrics: pd.DataFrame,
    evaluation_details: dict[str, dict],
    best_model_name: str,
) -> None:
    """เขียนรายงาน metrics แบบอ่านง่าย และคงชื่อไฟล์เดิมไว้เพื่อ compatibility."""
    metrics_path = CONFIG.output_dir / "feature_importance_stroke_metrics.txt"
    with metrics_path.open("w", encoding="utf-8") as f:
        f.write("Stroke Prediction Model Metrics\n")
        f.write("===============================\n\n")
        f.write("Target definition: ICD-10 I60-I69* in PrincipleDiagnosis only\n")
        f.write(f"Rows: {len(df):,}\n")
        f.write(f"Features before imputation: {len(feature_columns):,}\n")
        f.write(f"Stroke records: {int(y.sum()):,}\n")
        f.write(f"Non-stroke records: {int((y == 0).sum()):,}\n")
        f.write(f"Stroke prevalence: {y.mean() * 100:.2f}%\n")
        f.write(f"Best holdout model by ROC-AUC: {best_model_name}\n\n")

        f.write("Cross-Validation Summary\n")
        f.write("------------------------\n")
        f.write(cv_summary.to_string(index=False))
        f.write("\n\n")

        f.write("Holdout Metrics\n")
        f.write("---------------\n")
        f.write(holdout_metrics.to_string(index=False))
        f.write("\n\n")

        for model_name, details in evaluation_details.items():
            f.write(f"Confusion Matrix: {model_name}\n")
            f.write(str(details["confusion_matrix"]))
            f.write("\n\nClassification Report\n")
            f.write(details["classification_report"])
            f.write("\n\n")

    print(f"Saved metrics report: {metrics_path}")


def main() -> None:
    """ควบคุม workflow ทั้งหมดตั้งแต่โหลดข้อมูลจนถึง export output."""
    df, X, y, feature_columns = load_dataset(CONFIG)
    models = build_models(y, CONFIG)

    # holdout split ใช้ประเมิน final model หลังจาก train เสร็จ
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=CONFIG.test_size,
        random_state=CONFIG.random_state,
        stratify=y,
    )

    # 1) Cross-validation เพื่อดูความเสถียรของโมเดล
    cv_df = run_cross_validation(models, X, y, CONFIG)
    cv_summary = summarize_cv(cv_df)

    # 2) สร้าง model instances ใหม่สำหรับ final holdout training หลัง CV
    #    เพื่อไม่ reuse model object ที่ผ่านการ fit ใน fold สุดท้าย
    holdout_models = build_models(y_train, CONFIG)
    fitted_models, holdout_metrics, evaluation_details = train_holdout_models(
        holdout_models,
        X_train,
        y_train,
        X_test,
        y_test,
    )

    # 3) export feature importance ทั้งแบบรายโมเดลและแบบเปรียบเทียบ
    export_feature_importance(fitted_models, feature_columns)

    # 4) เลือก best model ด้วย ROC-AUC บน holdout แล้วเขียน metrics report
    best_model_name = select_best_model(holdout_metrics)
    write_metrics_report(
        df=df,
        y=y,
        feature_columns=feature_columns,
        cv_summary=cv_summary,
        holdout_metrics=holdout_metrics,
        evaluation_details=evaluation_details,
        best_model_name=best_model_name,
    )

    # 5) ทำ SHAP เฉพาะ best model เพื่อลดเวลาและโฟกัสที่โมเดลที่ใช้งานจริงมากที่สุด
    run_shap_analysis(
        model_name=best_model_name,
        model=fitted_models[best_model_name],
        X_test=X_test,
        y_test=y_test,
        feature_columns=feature_columns,
        config=CONFIG,
    )


if __name__ == "__main__":
    main()
