"""Stage 07 feature importance and dimensionality reduction.

อธิบายงานแบบย่อ:
1) อ่าน Extract Set 1/2/3 จาก Stage 05
2) ประเมิน 3 แนวทาง: ANOVA, PCA, ANOVA+PCA
3) ใช้ patient-level CV เพื่อคงแนวทางเดียวกับ pipeline หลัก
4) บังคับให้การ fit scaler/selector/PCA เกิดเฉพาะ training fold
   เพื่อลดความเสี่ยง data leakage
5) สรุปผลเป็นตารางพร้อมรายงาน .json/.md
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
class FeatureImportanceConfig:
    feature_dir: Path = Path("output/feature_engineering_output")
    model_dir: Path = Path("output/model_output")
    output_dir: Path = Path("output/feature_importance_output")
    patient_id_col: str = "patient_id"
    target_col: str = "stroke"
    random_state: int = 42
    max_folds: int = 5
    threshold: float = 0.5
    top_k_candidates: tuple[int, ...] = (5, 10, 15, 20, 30, 40, 50)
    pca_component_candidates: tuple[int, ...] = (2, 3, 5, 8, 10, 15, 20, 30)


FEATURE_FILES = {
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


def load_feature_tables(config: FeatureImportanceConfig) -> dict[str, pd.DataFrame]:
    """โหลด feature table เฉพาะชุด temporal ตามสเปก Stage 07."""
    tables: dict[str, pd.DataFrame] = {}
    for name, filename in FEATURE_FILES.items():
        path = config.feature_dir / filename
        if path.exists():
            tables[name] = pd.read_csv(path)
    if not tables:
        raise FileNotFoundError(f"No extract set files found in: {config.feature_dir}")
    return tables


def load_model_context(config: FeatureImportanceConfig) -> dict[str, object]:
    """อ่าน context จาก Stage 06 เพื่ออ้างอิงในรายงาน (ถ้ามี)."""
    report_path = config.model_dir / "modeling_report.json"
    if not report_path.exists():
        return {}
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def g_mean(sensitivity: float, specificity: float) -> float:
    """คำนวณ G-Mean สำหรับข้อมูล imbalanced."""
    return math.sqrt(max(sensitivity, 0.0) * max(specificity, 0.0))


def evaluate_predictions(y_true: list[int], y_pred: list[int]) -> dict[str, float | int]:
    """คำนวณ confusion-derived metrics ที่ใช้เทียบแต่ละ candidate."""
    from sklearn.metrics import confusion_matrix

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "g_mean": float(g_mean(sensitivity, specificity)),
    }


def prepare_xy(table: pd.DataFrame, config: FeatureImportanceConfig) -> tuple[pd.DataFrame, pd.Series]:
    """เตรียม X/y โดยใช้เฉพาะ numeric features และ target stroke."""
    required = [config.patient_id_col, config.target_col]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    clean = table.dropna(subset=[config.target_col]).copy()
    y = pd.to_numeric(clean[config.target_col], errors="coerce").astype(int)
    x = clean.drop(columns=[config.patient_id_col, config.target_col], errors="ignore")
    x = x.select_dtypes(include=[np.number]).copy()
    return x, y


def choose_cv(y: pd.Series, config: FeatureImportanceConfig):
    """เลือก CV strategy แบบปลอดภัยต่อ class imbalance.

    - class เดียว: ไม่สามารถ train/evaluate ได้ -> skip
    - minority class < 2: split ไม่ได้ -> skip
    - ชุดเล็ก: ใช้ LOOCV
    - ชุดใหญ่ขึ้น: ใช้ StratifiedKFold ตาม max_folds
    """
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


def sanitize_candidates(max_allowed: int, values: tuple[int, ...]) -> list[int]:
    """กรอง candidate k/components ให้ไม่เกินจำนวน feature จริง."""
    return sorted({value for value in values if 1 <= value <= max_allowed})


def make_pipeline(mode: str, k: int | None, n_components: int | None, config: FeatureImportanceConfig):
    """ประกอบ sklearn Pipeline ตามโหมดที่กำลังประเมิน.

    หมายเหตุสำคัญ:
    pipeline นี้จะถูก fit ในแต่ละ training fold เท่านั้น
    จึงช่วยคุม leakage สำหรับ imputer/scaler/selector/PCA
    """
    from sklearn.decomposition import PCA
    from sklearn.feature_selection import SelectKBest, f_classif
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    if mode == "anova":
        if k is None:
            raise ValueError("ANOVA mode requires k.")
        steps.append(("selector", SelectKBest(score_func=f_classif, k=k)))
    elif mode == "pca":
        if n_components is None:
            raise ValueError("PCA mode requires n_components.")
        steps.append(("pca", PCA(n_components=n_components, random_state=config.random_state)))
    elif mode == "anova_pca":
        if k is None or n_components is None:
            raise ValueError("ANOVA+PCA mode requires both k and n_components.")
        steps.append(("selector", SelectKBest(score_func=f_classif, k=k)))
        steps.append(("pca", PCA(n_components=n_components, random_state=config.random_state)))
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    steps.append(
        (
            "classifier",
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=config.random_state,
            ),
        )
    )
    return Pipeline(steps=steps)


def evaluate_candidate(
    x: pd.DataFrame,
    y: pd.Series,
    cv,
    config: FeatureImportanceConfig,
    mode: str,
    k: int | None,
    n_components: int | None,
) -> dict[str, object]:
    """ประเมิน candidate หนึ่งชุด (เช่น k=10 หรือ n_components=5) ด้วย CV."""
    rows: list[dict[str, object]] = []
    for fold_idx, (train_idx, test_idx) in enumerate(cv.split(x, y), start=1):
        model = make_pipeline(mode=mode, k=k, n_components=n_components, config=config)
        model.fit(x.iloc[train_idx], y.iloc[train_idx])
        prob = model.predict_proba(x.iloc[test_idx])[:, 1]
        pred = (prob >= config.threshold).astype(int)
        for true, predicted in zip(y.iloc[test_idx], pred):
            rows.append({"fold": fold_idx, "y_true": int(true), "y_pred": int(predicted)})
    pred_df = pd.DataFrame(rows)
    metrics = evaluate_predictions(
        pred_df["y_true"].astype(int).tolist(),
        pred_df["y_pred"].astype(int).tolist(),
    )
    return metrics


def rank_features_anova(x: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """ทำ global ANOVA ranking เพื่อรายงาน feature importance."""
    from sklearn.feature_selection import f_classif
    from sklearn.impute import SimpleImputer

    imputer = SimpleImputer(strategy="median")
    x_imputed = imputer.fit_transform(x)
    f_scores, p_values = f_classif(x_imputed, y)
    ranking = pd.DataFrame(
        {
            "feature": x.columns.tolist(),
            "f_score": f_scores.astype(float),
            "p_value": p_values.astype(float),
        }
    )
    return ranking.sort_values(["f_score", "p_value"], ascending=[False, True]).reset_index(drop=True)


def run_set_analysis(
    set_name: str,
    table: pd.DataFrame,
    config: FeatureImportanceConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """รันการวิเคราะห์ครบ 3 วิธีสำหรับ extract set เดียว.

    คืนค่าตาราง:
    - ranking
    - anova performance
    - pca performance
    - anova+pca performance
    - summary
    """
    x, y = prepare_xy(table, config)
    cv, cv_name = choose_cv(y, config)
    base_info = {
        "set_name": set_name,
        "n_patients": int(len(y)),
        "n_features": int(x.shape[1]),
        "positive_count": int((y == 1).sum()),
        "negative_count": int((y == 0).sum()),
        "cv_strategy": cv_name,
    }

    # ถ้า class distribution ไม่พร้อมหรือไม่มี numeric feature -> ข้ามอย่างโปร่งใส
    if cv is None or x.empty:
        status = "skipped"
        reason = cv_name if cv is None else "not_run_no_numeric_features"
        summary = {**base_info, "status": status, "skip_reason": reason}
        empty = pd.DataFrame()
        return empty, empty, empty, empty, summary

    ranking = rank_features_anova(x, y)
    k_candidates = sanitize_candidates(x.shape[1], config.top_k_candidates)
    pca_candidates = sanitize_candidates(x.shape[1], config.pca_component_candidates)

    # 1) ANOVA: วนลองหลายค่า k แล้วเก็บ metric
    anova_rows = []
    for k in k_candidates:
        metrics = evaluate_candidate(x, y, cv, config, mode="anova", k=k, n_components=None)
        anova_rows.append({"set_name": set_name, "method": "anova", "k": int(k), "n_components": np.nan, **metrics})
    anova_table = pd.DataFrame(anova_rows).sort_values("g_mean", ascending=False).reset_index(drop=True)

    # 2) PCA: วนลองหลายจำนวน components แล้วเก็บ metric
    pca_rows = []
    for n_comp in pca_candidates:
        metrics = evaluate_candidate(x, y, cv, config, mode="pca", k=None, n_components=n_comp)
        pca_rows.append(
            {"set_name": set_name, "method": "pca", "k": np.nan, "n_components": int(n_comp), **metrics}
        )
    pca_table = pd.DataFrame(pca_rows).sort_values("g_mean", ascending=False).reset_index(drop=True)

    # 3) ANOVA+PCA: เลือก top-k ก่อน แล้วค่อยลดมิติด้วย PCA
    combo_rows = []
    for k in k_candidates:
        valid_components = sanitize_candidates(k, config.pca_component_candidates)
        for n_comp in valid_components:
            metrics = evaluate_candidate(x, y, cv, config, mode="anova_pca", k=k, n_components=n_comp)
            combo_rows.append(
                {
                    "set_name": set_name,
                    "method": "anova_pca",
                    "k": int(k),
                    "n_components": int(n_comp),
                    **metrics,
                }
            )
    combo_table = pd.DataFrame(combo_rows).sort_values("g_mean", ascending=False).reset_index(drop=True)

    # สรุป best candidate ของแต่ละวิธีเพื่อใช้ในรายงาน validation ภายหลัง
    best_rows = []
    if not anova_table.empty:
        best_rows.append(anova_table.iloc[0].to_dict())
    if not pca_table.empty:
        best_rows.append(pca_table.iloc[0].to_dict())
    if not combo_table.empty:
        best_rows.append(combo_table.iloc[0].to_dict())
    best_table = pd.DataFrame(best_rows)

    summary = {
        **base_info,
        "status": "completed",
        "skip_reason": "",
        "best_anova_g_mean": float(anova_table.iloc[0]["g_mean"]) if not anova_table.empty else None,
        "best_pca_g_mean": float(pca_table.iloc[0]["g_mean"]) if not pca_table.empty else None,
        "best_anova_pca_g_mean": float(combo_table.iloc[0]["g_mean"]) if not combo_table.empty else None,
        "best_anova_k": int(anova_table.iloc[0]["k"]) if not anova_table.empty else None,
        "best_pca_components": int(pca_table.iloc[0]["n_components"]) if not pca_table.empty else None,
        "best_combo_k": int(combo_table.iloc[0]["k"]) if not combo_table.empty else None,
        "best_combo_components": int(combo_table.iloc[0]["n_components"]) if not combo_table.empty else None,
    }
    ranking["set_name"] = set_name
    return ranking, anova_table, pca_table, combo_table, best_table, summary


def build_markdown_report(
    summary_df: pd.DataFrame,
    model_context: dict[str, object],
    output_dir: Path,
) -> str:
    """สร้างรายงาน markdown ให้ทีมอ่านผลเร็วโดยไม่เปิด CSV ทุกไฟล์."""
    completed = summary_df[summary_df["status"] == "completed"] if "status" in summary_df else pd.DataFrame()
    skipped = summary_df[summary_df["status"] == "skipped"] if "status" in summary_df else pd.DataFrame()

    lines = [
        "# Feature Importance Report",
        "",
        "## Summary",
        "",
        f"- Output directory: `{output_dir}`",
        f"- Sets analyzed: {len(summary_df)}",
        f"- Completed: {len(completed)}",
        f"- Skipped: {len(skipped)}",
    ]
    if model_context:
        lines.append(f"- Stage 06 best model context: `{model_context.get('best_model', '')}`")
        lines.append(f"- Stage 06 best G-Mean context: `{model_context.get('best_g_mean', None)}`")

    lines.extend(
        [
            "",
            "## Leakage Guard",
            "",
            "- `SelectKBest`, scaler, and PCA are fitted inside each training fold only.",
            "- Evaluation uses patient-level CV strategy inherited from class distribution checks.",
            "",
            "## Interpretability Notes",
            "",
            "- ANOVA ranking remains directly interpretable at original feature level.",
            "- PCA-based methods reduce multicollinearity but component-level interpretation is indirect.",
            "",
            "## Outputs",
            "",
            "- `feature_importance_summary.csv`",
            "- `anova_feature_ranking.csv`",
            "- `anova_performance.csv`",
            "- `pca_performance.csv`",
            "- `anova_pca_performance.csv`",
            "- `best_feature_importance_choices.csv`",
            "- `feature_importance_report.json`",
            "- `feature_importance_report.md`",
        ]
    )
    if not skipped.empty:
        lines.extend(["", "## Skipped Sets", ""])
        for _, row in skipped.iterrows():
            lines.append(f"- `{row['set_name']}` skipped: {row.get('skip_reason', '')}")

    return "\n".join(lines) + "\n"


def run_feature_importance(config: FeatureImportanceConfig) -> dict[str, object]:
    """entrypoint หลักของ Stage 07.

    ลำดับงาน:
    1) โหลดข้อมูล
    2) วิเคราะห์ทีละ extract set
    3) เขียน artifacts ทั้งตารางละเอียดและ summary
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)
    tables = load_feature_tables(config)
    model_context = load_model_context(config)

    ranking_tables = []
    anova_tables = []
    pca_tables = []
    combo_tables = []
    best_tables = []
    summary_rows = []

    for set_name, table in tables.items():
        # ประมวลผลแต่ละชุดแยกกัน เพื่อให้ trace/debug ง่าย
        result = run_set_analysis(set_name=set_name, table=table, config=config)
        if len(result) == 6:
            ranking, anova_table, pca_table, combo_table, best_table, summary = result
        else:
            ranking, anova_table, pca_table, combo_table, summary = result
            best_table = pd.DataFrame()
        summary_rows.append(summary)
        if not ranking.empty:
            ranking_tables.append(ranking)
        if not anova_table.empty:
            anova_tables.append(anova_table)
        if not pca_table.empty:
            pca_tables.append(pca_table)
        if not combo_table.empty:
            combo_tables.append(combo_table)
        if not best_table.empty:
            best_tables.append(best_table)

    summary_df = pd.DataFrame(summary_rows)
    write_csv(summary_df, config.output_dir / "feature_importance_summary.csv")
    write_csv(pd.concat(ranking_tables, ignore_index=True) if ranking_tables else pd.DataFrame(), config.output_dir / "anova_feature_ranking.csv")
    write_csv(pd.concat(anova_tables, ignore_index=True) if anova_tables else pd.DataFrame(), config.output_dir / "anova_performance.csv")
    write_csv(pd.concat(pca_tables, ignore_index=True) if pca_tables else pd.DataFrame(), config.output_dir / "pca_performance.csv")
    write_csv(pd.concat(combo_tables, ignore_index=True) if combo_tables else pd.DataFrame(), config.output_dir / "anova_pca_performance.csv")
    write_csv(pd.concat(best_tables, ignore_index=True) if best_tables else pd.DataFrame(), config.output_dir / "best_feature_importance_choices.csv")

    report = {
        "feature_dir": str(config.feature_dir),
        "model_dir": str(config.model_dir),
        "output_dir": str(config.output_dir),
        "sets_seen": list(tables.keys()),
        "sets_completed": int((summary_df["status"] == "completed").sum()) if "status" in summary_df else 0,
        "sets_skipped": int((summary_df["status"] == "skipped").sum()) if "status" in summary_df else 0,
    }
    write_json(report, config.output_dir / "feature_importance_report.json")
    (config.output_dir / "feature_importance_report.md").write_text(
        build_markdown_report(summary_df, model_context, config.output_dir),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    """รองรับการรันผ่าน CLI และ override path ได้."""
    parser = argparse.ArgumentParser(description="Run Stage 07 feature importance.")
    parser.add_argument("--feature-dir", default=str(FeatureImportanceConfig.feature_dir))
    parser.add_argument("--model-dir", default=str(FeatureImportanceConfig.model_dir))
    parser.add_argument("--output-dir", default=str(FeatureImportanceConfig.output_dir))
    parser.add_argument("--max-folds", type=int, default=FeatureImportanceConfig.max_folds)
    parser.add_argument("--threshold", type=float, default=FeatureImportanceConfig.threshold)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = FeatureImportanceConfig(
        feature_dir=Path(args.feature_dir),
        model_dir=Path(args.model_dir),
        output_dir=Path(args.output_dir),
        max_folds=args.max_folds,
        threshold=args.threshold,
    )
    report = run_feature_importance(config)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
