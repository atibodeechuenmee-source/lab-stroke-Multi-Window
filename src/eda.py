# =========================
# 1. Import Libraries
# =========================
# ไฟล์นี้ใช้สำหรับทำ EDA (Exploratory Data Analysis) เบื้องต้นจากไฟล์ Excel
# โดยอ่านข้อมูลผู้ป่วยเข้ามา ตรวจสอบโครงสร้างข้อมูล ค่าที่หายไป การกระจายตัว
# ความสัมพันธ์ระหว่างตัวแปร และบันทึกกราฟ/ตารางผลลัพธ์ไว้ในโฟลเดอร์ output/eda_output
import shutil
import re
import sys
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib

# บังคับให้ matplotlib ใช้ backend แบบ Agg เพื่อให้สร้างไฟล์รูปได้โดยไม่ต้องเปิดหน้าต่าง GUI
# เหมาะกับการรันผ่าน terminal, CI, หรือเครื่องที่ไม่มี display server
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

if hasattr(sys.stdout, "reconfigure"):
    # ตั้งค่า stdout เป็น UTF-8 เพื่อให้ข้อความภาษาไทย/สัญลักษณ์พิเศษพิมพ์ออก console ได้ถูกต้อง
    sys.stdout.reconfigure(encoding="utf-8")

# ตั้งค่า style และ font ของกราฟทั้งหมดให้ใช้ร่วมกันทั้งไฟล์
# Tahoma ถูกใส่ไว้ก่อนเพื่อรองรับภาษาไทยบน Windows ถ้าไม่มีจะ fallback ไป font ถัดไป
sns.set(style="whitegrid")
plt.rcParams["font.family"] = ["Tahoma", "DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# โฟลเดอร์สำหรับเก็บผลลัพธ์ EDA เช่น heatmap, histogram, boxplot และไฟล์ CSV
OUTPUT_DIR = Path("output") / "eda_output"

# ไฟล์ Excel ต้นทางและไฟล์ cache แบบ pickle
# การใช้ cache ช่วยให้รันซ้ำได้เร็วขึ้น เพราะไม่ต้องอ่าน Excel ใหม่ทุกครั้งถ้าไฟล์ต้นทางยังไม่เปลี่ยน
INPUT_EXCEL = Path("data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx")
DATA_CACHE = Path("data/interim/preprocess_input_cache.pkl")
PATIENT_COHORT_PATH = Path("output/target_cohort_output/patient_level_90d_cohort.csv")

# ค่าคงที่สำหรับควบคุมคุณภาพและขนาดของกราฟ
PLOT_DPI = 220
MISSING_HEATMAP_MAX_ROWS = 1500
PAIRPLOT_MAX_ROWS = 500
PAIRPLOT_MAX_COLUMNS = 6
BOXPLOT_MAX_ROWS = 20000
HIST_COLUMNS_PER_FIGURE = 12
HIST_COLUMNS_PER_ROW = 3
CORRELATION_ANNOTATION_LIMIT = 14
CORRELATION_MIN_ABS_TO_LABEL = 0.30

# ชื่อ column สำคัญที่ใช้ในกราฟเฉพาะทาง
TC_HDL_RATIO_COLUMN = "TC:HDL_ratio"
AGE_COLUMN = "age"
EVENT_MARKER_COLUMN = "stroke_flag"
TARGET_COLUMN = "stroke_3m"
STROKE_PATTERN = re.compile(r"^I6[0-9][0-9A-Z]*$", re.IGNORECASE)


def clean_output_dir():
    # ล้าง output เก่าทุกครั้งก่อนเริ่ม EDA เพื่อไม่ให้ไฟล์จากการรันครั้งก่อนปนกับผลลัพธ์ล่าสุด
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for item in OUTPUT_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    print(f"Cleaned output directory: {OUTPUT_DIR}")


def safe_filename(name):
    # แปลงชื่อ column ให้ปลอดภัยสำหรับใช้เป็นชื่อไฟล์
    # ตัวอักษรที่ไม่ใช่ A-Z, a-z, 0-9, underscore, dot หรือ hyphen จะถูกแทนด้วย "_"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("_")


def readable_label(name, max_len=22):
    # ทำให้ label บนกราฟไม่ยาวเกินไปเพื่อลดปัญหาข้อความทับกัน
    # ถ้าชื่อยาวเกิน max_len จะตัดท้ายและใส่ "..."
    label = str(name)
    if len(label) <= max_len:
        return label
    return label[: max_len - 1] + "..."


def save_current_plot(filename):
    # บันทึกกราฟปัจจุบันที่สร้างด้วย pyplot interface เช่น plt.figure()
    # จากนั้นปิด figure เพื่อคืนหน่วยความจำและป้องกันกราฟซ้อนกันในการวนลูป
    path = OUTPUT_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=PLOT_DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {path}")


def save_figure(fig, filename):
    # บันทึก figure object ที่สร้างจาก fig, ax = plt.subplots()
    # ใช้ในกรณีที่ต้องควบคุมหลาย axes หรือจัด layout เอง
    path = OUTPUT_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=PLOT_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot: {path}")


def save_table(data, filename):
    # บันทึก DataFrame เป็น CSV ด้วย UTF-8 with BOM เพื่อให้ Excel บน Windows เปิดภาษาไทยได้ถูกต้อง
    path = OUTPUT_DIR / filename
    data.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved table: {path}")


def build_stroke_flag(data):
    if "PrincipleDiagnosis" not in data.columns:
        return None
    diagnosis = data["PrincipleDiagnosis"].astype("string").str.strip().fillna("")
    return diagnosis.str.contains(STROKE_PATTERN, regex=True, na=False).astype(int)


def add_target_column(data):
    data = data.copy()
    stroke_flag = build_stroke_flag(data)
    if stroke_flag is not None:
        data[EVENT_MARKER_COLUMN] = stroke_flag
    return data


def numeric_columns_for_eda(data):
    # เลือกเฉพาะ column เชิงตัวเลขสำหรับการวิเคราะห์เชิงสถิติและกราฟ numeric
    numeric_cols = data.select_dtypes(include=np.number).columns.tolist()

    # ตัด column ที่มีลักษณะเป็นรหัส/identifier ออก เพราะไม่ควรนำไปตีความเป็น feature ต่อเนื่อง
    id_like = {"hn"}
    return [col for col in numeric_cols if str(col).lower() not in id_like]


def save_eda_summary_tables(data):
    # สร้างตารางสรุป schema ราย column เพื่อดูชนิดข้อมูล จำนวน non-null, missing และ unique values
    row_count = len(data)
    column_summary = pd.DataFrame(
        {
            "column": data.columns,
            "dtype": [str(dtype) for dtype in data.dtypes],
            "non_null_count": data.notna().sum().values,
            "missing_count": data.isna().sum().values,
            "missing_percent": data.isna().mean().mul(100).round(2).values,
            "unique_count": data.nunique(dropna=True).values,
        }
    )
    column_summary["row_count"] = row_count
    save_table(column_summary, "column_types.csv")

    # สร้างตาราง missing values โดยเรียง column ที่มี missing เยอะสุดไว้ด้านบน
    missing_summary = (
        column_summary[["column", "missing_count", "missing_percent", "non_null_count", "row_count"]]
        .sort_values(["missing_count", "column"], ascending=[False, True])
        .reset_index(drop=True)
    )
    save_table(missing_summary, "missing_summary.csv")

    # สร้างตารางสถิติของ numeric columns แบบ transpose เพื่อให้อ่านราย feature ง่าย
    numeric_data = data[numeric_columns_for_eda(data)]
    if numeric_data.empty:
        print("No numeric columns found; skipped numeric_summary.csv")
        return

    numeric_summary = numeric_data.describe().T.reset_index().rename(columns={"index": "column"})
    numeric_summary["missing_count"] = numeric_data.isna().sum().values
    numeric_summary["missing_percent"] = numeric_data.isna().mean().mul(100).round(2).values
    numeric_summary["unique_count"] = numeric_data.nunique(dropna=True).values
    save_table(numeric_summary, "numeric_summary.csv")

    percentile_summary = (
        numeric_data.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
        .T.reset_index()
        .rename(
            columns={
                "index": "column",
                0.01: "p01",
                0.05: "p05",
                0.25: "p25",
                0.5: "p50",
                0.75: "p75",
                0.95: "p95",
                0.99: "p99",
            }
        )
    )
    save_table(percentile_summary, "percentile_summary.csv")


def save_outlier_summary(data):
    numeric_data = data[numeric_columns_for_eda(data)]
    records = []
    for col in numeric_data.columns:
        series = numeric_data[col].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        low_count = int((series < lower).sum())
        high_count = int((series > upper).sum())
        records.append(
            {
                "column": col,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_fence": lower,
                "upper_fence": upper,
                "low_outlier_count": low_count,
                "high_outlier_count": high_count,
                "total_outlier_count": low_count + high_count,
                "outlier_percent_of_non_null": round((low_count + high_count) / max(len(series), 1) * 100, 2),
            }
        )
    save_table(pd.DataFrame(records), "outlier_summary_iqr.csv")


def plot_missing_values_heatmap(data):
    # สร้าง heatmap แสดงตำแหน่ง missing value ในระดับ cell
    # ช่องที่เป็น True หมายถึงข้อมูลใน cell นั้นหายไป
    missing_data = data.isnull()

    # ถ้าข้อมูลมีหลายแถวมาก จะสุ่มตัวอย่างมาแสดงเพื่อให้รูปไม่ใหญ่เกินและอ่านง่ายขึ้น
    if len(missing_data) > MISSING_HEATMAP_MAX_ROWS:
        missing_data = missing_data.sample(MISSING_HEATMAP_MAX_ROWS, random_state=42).sort_index()

    # ปรับความกว้างของรูปตามจำนวน column แต่จำกัดไม่ให้เล็กหรือใหญ่เกินไป
    width = max(14, min(28, 0.45 * len(missing_data.columns)))
    fig, ax = plt.subplots(figsize=(width, 7))
    sns.heatmap(missing_data, cbar=False, cmap="viridis", yticklabels=False, ax=ax)
    ax.set_title(
        f"Missing Values Heatmap (sampled {len(missing_data):,} of {len(data):,} rows)",
        fontsize=16,
        pad=16,
    )
    ax.set_xlabel("Columns")
    ax.set_ylabel("Rows")
    ax.set_xticklabels([readable_label(col, 18) for col in missing_data.columns], rotation=45, ha="right", fontsize=9)
    save_figure(fig, "missing_values_heatmap.png")


def plot_missing_percent(data):
    # คำนวณเปอร์เซ็นต์ missing value ของแต่ละ column
    # mean() กับค่า boolean จะให้สัดส่วน True แล้วคูณ 100 เพื่อแปลงเป็นเปอร์เซ็นต์
    missing_pct = data.isna().mean().mul(100).sort_values(ascending=True)

    # แสดงเฉพาะ column ที่มี missing จริง เพื่อไม่ให้กราฟรกด้วยค่า 0%
    missing_pct = missing_pct[missing_pct > 0]
    if missing_pct.empty:
        print("No missing values found; skipped missing_values_percent.png")
        return

    # ใช้ bar chart แนวนอนเพื่อให้ชื่อ column ที่ยาวยังพออ่านได้
    height = max(5, 0.35 * len(missing_pct))
    fig, ax = plt.subplots(figsize=(11, height))
    bars = ax.barh([readable_label(col, 32) for col in missing_pct.index], missing_pct.values, color="#4c78a8")
    ax.bar_label(bars, labels=[f"{value:.1f}%" for value in missing_pct.values], padding=4, fontsize=9)
    ax.set_title("Missing Values by Column (%)", fontsize=16, pad=14)
    ax.set_xlabel("Missing values (%)")
    ax.set_xlim(0, max(100, missing_pct.max() * 1.12))
    ax.grid(axis="x", alpha=0.25)
    ax.grid(axis="y", visible=False)
    save_figure(fig, "missing_values_percent.png")


def plot_feature_distributions(data):
    # สร้างกราฟ distribution ของ numeric features ทั้งหมด
    # ตัวแปรที่มี unique values น้อยจะใช้ countplot ส่วนตัวแปรต่อเนื่องจะใช้ histogram
    numeric_cols = numeric_columns_for_eda(data)
    if not numeric_cols:
        print("No numeric columns found; skipped feature distributions.")
        return

    # แบ่ง features ออกเป็นหลายรูปตาม HIST_COLUMNS_PER_FIGURE เพื่อไม่ให้แต่ละรูปแน่นเกินไป
    for start in range(0, len(numeric_cols), HIST_COLUMNS_PER_FIGURE):
        columns = numeric_cols[start : start + HIST_COLUMNS_PER_FIGURE]
        ncols = min(HIST_COLUMNS_PER_ROW, len(columns))
        nrows = int(np.ceil(len(columns) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 3.8 * nrows))
        axes = np.atleast_1d(axes).ravel()

        for ax, col in zip(axes, columns):
            series = data[col].dropna()
            unique_count = series.nunique()

            # ถ้าค่าที่เป็นไปได้มีน้อย ให้มองเหมือน categorical/discrete variable
            # เพื่อให้เห็นจำนวนของแต่ละค่าอย่างชัดเจน
            if unique_count <= 8:
                order = sorted(series.unique())
                sns.countplot(x=series, order=order, ax=ax, color="#4c78a8")
                ax.set_xlabel("")
            else:
                # ถ้าค่ามีความหลากหลายสูง ให้ใช้ histogram เพื่อดูรูปทรงการกระจายตัว
                sns.histplot(series, bins=30, kde=False, ax=ax, color="#4c78a8")
                ax.set_xlabel("")
            ax.set_title(readable_label(col, 28), fontsize=12, pad=8)
            ax.tick_params(axis="x", labelrotation=30, labelsize=8)
            ax.tick_params(axis="y", labelsize=8)
            ax.grid(axis="y", alpha=0.25)
            ax.grid(axis="x", visible=False)

        for ax in axes[len(columns) :]:
            # ปิด subplot ที่เหลือในกรณีจำนวน feature ไม่พอดีกับ grid
            ax.axis("off")

        suffix = "" if start == 0 else f"_{(start // HIST_COLUMNS_PER_FIGURE) + 1}"
        fig.suptitle("Feature Distributions", fontsize=18, y=1.01)
        save_figure(fig, f"feature_distributions{suffix}.png")


def plot_correlation_matrix(data):
    # สร้าง correlation matrix จาก numeric features เพื่อดูความสัมพันธ์เชิงเส้นระหว่างตัวแปร
    numeric_data = data[numeric_columns_for_eda(data)]
    corr = numeric_data.corr(numeric_only=True)
    if corr.empty:
        print("No numeric correlations found; skipped correlation matrix.")
        return

    # ถ้าจำนวน feature ไม่มาก จะแสดงตัวเลข correlation ใน heatmap
    # แต่ถ้าเยอะเกินไปจะซ่อนตัวเลขเพื่อลดปัญหาข้อความทับกัน
    show_annotations = len(corr) <= CORRELATION_ANNOTATION_LIMIT
    annot = False
    if show_annotations:
        # แสดง label เฉพาะคู่ที่มี absolute correlation สูงพอ ยกเว้น diagonal ที่เป็น 1.00
        annot = corr.where(corr.abs() >= CORRELATION_MIN_ABS_TO_LABEL).round(2).astype(str)
        annot = annot.mask(corr.abs() < CORRELATION_MIN_ABS_TO_LABEL, "")
        np.fill_diagonal(annot.values, "1.00")

    # ปรับขนาดรูปตามจำนวน features เพื่อให้ matrix อ่านได้ในหลายขนาดข้อมูล
    size = max(10, min(22, 0.62 * len(corr)))
    fig, ax = plt.subplots(figsize=(size + 2, size))
    sns.heatmap(
        corr,
        annot=annot if show_annotations else False,
        fmt="",
        cmap="coolwarm",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.35,
        linecolor="white",
        cbar_kws={"shrink": 0.82, "label": "Correlation"},
        annot_kws={"fontsize": 8},
        ax=ax,
    )
    ax.set_title(
        "Correlation Matrix" if show_annotations else "Correlation Matrix (labels hidden to avoid overlap)",
        fontsize=18,
        pad=16,
    )
    ax.set_xticklabels([readable_label(col, 18) for col in corr.columns], rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels([readable_label(col, 18) for col in corr.index], rotation=0, fontsize=9)
    save_figure(fig, "correlation_matrix.png")

    # สร้างตารางจัดอันดับคู่ feature ตามค่า absolute correlation
    # ใช้เฉพาะสามเหลี่ยมบนของ matrix เพื่อไม่ให้คู่ซ้ำ เช่น A-B และ B-A
    strong_pairs = (
        corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        .stack()
        .rename("correlation")
        .reset_index()
    )
    strong_pairs.columns = ["feature_1", "feature_2", "correlation"]
    strong_pairs["abs_correlation"] = strong_pairs["correlation"].abs()
    strong_pairs = strong_pairs.sort_values("abs_correlation", ascending=False)
    save_table(strong_pairs, "correlation_pairs_ranked.csv")


def plot_boxplots(data):
    # สร้าง boxplot แยกไฟล์ต่อ numeric column เพื่อดูค่าผิดปกติและการกระจายแบบ quartile
    boxplot_df = data[numeric_columns_for_eda(data)]
    if len(boxplot_df) > BOXPLOT_MAX_ROWS:
        # ถ้าข้อมูลใหญ่เกินไป จะสุ่มแถวเพื่อลดเวลาและขนาดไฟล์ของกราฟ
        boxplot_df = boxplot_df.sample(BOXPLOT_MAX_ROWS, random_state=42)

    for col in boxplot_df.columns:
        plt.figure(figsize=(7, 3.6))
        sns.boxplot(x=boxplot_df[col].dropna(), color="#4c78a8", fliersize=1.5, linewidth=1)
        plt.title(f"Boxplot of {readable_label(col, 36)}")
        plt.xlabel(readable_label(col, 36))
        save_current_plot(f"boxplot_{safe_filename(col)}.png")


def plot_pairplot(data):
    # สร้าง scatter matrix เพื่อดูความสัมพันธ์แบบคู่ ๆ ระหว่าง numeric features
    # จำกัดจำนวน column และ row เพราะ pairplot มีต้นทุนสูงและอ่านยากเมื่อ feature เยอะ
    pairplot_data = data[numeric_columns_for_eda(data)].iloc[:, :PAIRPLOT_MAX_COLUMNS]
    if pairplot_data.empty:
        print("No numeric columns found; skipped pairplot.")
        return
    if len(pairplot_data) > PAIRPLOT_MAX_ROWS:
        # สุ่ม row เพื่อลดขนาดกราฟและเวลาในการสร้างรูป
        pairplot_data = pairplot_data.sample(PAIRPLOT_MAX_ROWS, random_state=42)

    axes = pd.plotting.scatter_matrix(
        pairplot_data,
        figsize=(11, 11),
        diagonal="hist",
        alpha=0.35,
        s=10,
        marker=".",
        hist_kwds={"bins": 20, "color": "#4c78a8"},
    )
    fig = axes[0, 0].figure
    for ax in axes.ravel():
        ax.tick_params(axis="both", labelsize=7)
        ax.xaxis.label.set_size(8)
        ax.yaxis.label.set_size(8)
        ax.xaxis.label.set_rotation(30)
    fig.suptitle(
        f"Pairplot of First {pairplot_data.shape[1]} Numeric Features (sampled {len(pairplot_data):,} rows)",
        y=1.01,
        fontsize=14,
    )
    save_figure(fig, "pairplot.png")


def plot_target_analysis(data):
    # ตรวจ distribution ของ event marker ระดับ record เพื่อใช้ประกอบการสร้าง patient-level target
    if EVENT_MARKER_COLUMN not in data.columns:
        print(f"Column '{EVENT_MARKER_COLUMN}' not found; skipped record-level event marker analysis.")
        return

    plt.figure(figsize=(6, 4))
    ax = sns.countplot(x=EVENT_MARKER_COLUMN, data=data, color="#4c78a8")
    ax.bar_label(ax.containers[0], fontsize=9)
    plt.title("Distribution of Record-Level Stroke Event Marker")
    plt.xlabel("stroke_flag")
    plt.ylabel("Records")
    save_current_plot("stroke_flag_distribution.png")

    target_counts = (
        data[EVENT_MARKER_COLUMN]
        .value_counts(dropna=False)
        .rename_axis(EVENT_MARKER_COLUMN)
        .reset_index(name="record_count")
        .sort_values(EVENT_MARKER_COLUMN)
    )
    target_counts["record_percent"] = (target_counts["record_count"] / len(data) * 100).round(2)
    save_table(target_counts, "record_event_marker_distribution.csv")

    # ดูค่าเฉลี่ยของแต่ละ numeric feature แยกตาม record-level event marker
    # ช่วยให้เห็นเบื้องต้นว่า feature ใดมีแนวโน้มต่างกันระหว่างกลุ่ม
    grouped_mean = data.groupby(EVENT_MARKER_COLUMN).mean(numeric_only=True).reset_index()
    print("\nMean values grouped by record-level stroke_flag:")
    print(grouped_mean)
    save_table(grouped_mean, "stroke_flag_grouped_mean.csv")


def plot_patient_level_target_analysis():
    # Target หลักของโจทย์ prediction คือ stroke_3m ระดับคนไข้ ไม่ใช่ stroke_flag ระดับ record
    if not PATIENT_COHORT_PATH.exists():
        print(f"Patient cohort not found: {PATIENT_COHORT_PATH}; skipped stroke_3m target analysis.")
        return None

    patient_df = pd.read_csv(PATIENT_COHORT_PATH)
    if TARGET_COLUMN not in patient_df.columns:
        print(f"Column '{TARGET_COLUMN}' not found in {PATIENT_COHORT_PATH}; skipped stroke_3m target analysis.")
        return None

    plt.figure(figsize=(6, 4))
    ax = sns.countplot(x=TARGET_COLUMN, data=patient_df, color="#4c78a8")
    ax.bar_label(ax.containers[0], fontsize=9)
    plt.title("Distribution of Patient-Level 90-Day Stroke Target")
    plt.xlabel("stroke_3m")
    plt.ylabel("Patients")
    save_current_plot("stroke_3m_distribution.png")

    target_counts = (
        patient_df[TARGET_COLUMN]
        .value_counts(dropna=False)
        .rename_axis(TARGET_COLUMN)
        .reset_index(name="patient_count")
        .sort_values(TARGET_COLUMN)
    )
    target_counts["patient_percent"] = (target_counts["patient_count"] / len(patient_df) * 100).round(2)
    save_table(target_counts, "patient_level_target_distribution.csv")

    return {
        "patient_count": int(len(patient_df)),
        "positive_patients": int(patient_df[TARGET_COLUMN].sum()),
        "negative_patients": int((patient_df[TARGET_COLUMN] == 0).sum()),
        "prevalence_percent": round(float(patient_df[TARGET_COLUMN].mean() * 100), 2),
    }


def plot_age_vs_tc_hdl_ratio(data):
    # สร้าง scatter plot ระหว่าง age และ TC:HDL_ratio โดยใช้ชื่อ column จริงใน dataset
    # ถ้ามี stroke_flag จะใช้เป็นสีของจุดเพื่อดู event marker ระดับ record เท่านั้น
    required_columns = {AGE_COLUMN, TC_HDL_RATIO_COLUMN}
    if not required_columns.issubset(data.columns):
        print(f"Columns {sorted(required_columns)} not found; skipped age_vs_tc_hdl_ratio.png")
        return

    plt.figure(figsize=(6, 4))
    hue = EVENT_MARKER_COLUMN if EVENT_MARKER_COLUMN in data.columns else None
    sns.scatterplot(x=AGE_COLUMN, y=TC_HDL_RATIO_COLUMN, hue=hue, data=data, alpha=0.35, s=12)
    plt.title("Age vs TC/HDL Ratio")
    save_current_plot("age_vs_TC_HDL_ratio.png")


def load_input_data():
    # โหลดข้อมูลจาก cache ถ้า cache มีอยู่และใหม่กว่า/เท่ากับไฟล์ Excel ต้นทาง
    # วิธีนี้ช่วยลดเวลาอ่าน Excel ซึ่งมักช้ากว่า pickle มาก
    if DATA_CACHE.exists() and DATA_CACHE.stat().st_mtime >= INPUT_EXCEL.stat().st_mtime:
        print(f"Loading cached data: {DATA_CACHE}", flush=True)
        return pd.read_pickle(DATA_CACHE)

    # ถ้าไม่มี cache หรือไฟล์ Excel ถูกแก้ไขใหม่กว่า cache ให้อ่านจาก Excel แล้วสร้าง cache ใหม่
    print(f"Reading Excel data: {INPUT_EXCEL}", flush=True)
    data = pd.read_excel(INPUT_EXCEL)
    DATA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    data.to_pickle(DATA_CACHE)
    print(f"Saved data cache: {DATA_CACHE}", flush=True)
    return data


def write_eda_findings_summary(data, patient_target_summary=None):
    missing = data.isna().mean().mul(100).sort_values(ascending=False)
    high_missing = missing[missing >= 50]
    moderate_missing = missing[(missing >= 5) & (missing < 50)]
    numeric_cols = numeric_columns_for_eda(data)

    corr_path = OUTPUT_DIR / "correlation_pairs_ranked.csv"
    top_correlations = []
    if corr_path.exists():
        top_correlations = pd.read_csv(corr_path).head(10).to_dict(orient="records")

    event_marker_summary = None
    if EVENT_MARKER_COLUMN in data.columns:
        positives = int(data[EVENT_MARKER_COLUMN].sum())
        event_marker_summary = {
            "positive_records": positives,
            "negative_records": int((data[EVENT_MARKER_COLUMN] == 0).sum()),
            "prevalence_percent": round(positives / max(len(data), 1) * 100, 2),
        }

    leakage_risk_columns = [
        col for col in ["PrincipleDiagnosis", "ComorbidityDiagnosis", "ยาที่ได้รับ", "ตำบล"] if col in data.columns
    ]
    payload = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "input_path": str(INPUT_EXCEL),
        "row_count": int(len(data)),
        "column_count": int(len(data.columns)),
        "numeric_feature_count": len(numeric_cols),
        "primary_modeling_target": TARGET_COLUMN,
        "primary_modeling_target_level": "patient",
        "patient_target_summary": patient_target_summary,
        "record_event_marker": EVENT_MARKER_COLUMN if EVENT_MARKER_COLUMN in data.columns else None,
        "record_event_marker_summary": event_marker_summary,
        "high_missing_features": high_missing.round(2).to_dict(),
        "moderate_missing_features": moderate_missing.round(2).to_dict(),
        "top_correlations": top_correlations,
        "checks": {
            "eda_is_descriptive": True,
            "preprocessing_rules_for_modeling_should_be_refit_on_train_only": True,
            "derived_feature_caution": "TC:HDL_ratio depends on cholesterol and HDL",
            "leakage_risk_columns": leakage_risk_columns,
        },
    }

    json_path = OUTPUT_DIR / "eda_findings_summary.json"
    md_path = OUTPUT_DIR / "eda_findings_summary.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# EDA Findings Summary",
        "",
        f"- Run at: {payload['run_at']}",
        f"- Input: `{payload['input_path']}`",
        f"- Rows: {payload['row_count']:,}",
        f"- Columns: {payload['column_count']:,}",
        f"- Numeric features: {payload['numeric_feature_count']}",
        f"- Primary modeling target: `{TARGET_COLUMN}` (patient-level)",
    ]
    if patient_target_summary:
        lines.extend(
            [
                f"- Patient cohort: {patient_target_summary['patient_count']:,}",
                f"- Stroke positive patients: {patient_target_summary['positive_patients']:,}",
                f"- Patient-level stroke prevalence: {patient_target_summary['prevalence_percent']}%",
            ]
        )
    if event_marker_summary:
        lines.extend(
            [
                f"- Record-level stroke event marker records: {event_marker_summary['positive_records']:,}",
                f"- Record-level event marker prevalence: {event_marker_summary['prevalence_percent']}%",
            ]
        )

    lines.extend(["", "## High Missing Features", ""])
    if payload["high_missing_features"]:
        for col, pct in payload["high_missing_features"].items():
            lines.append(f"- `{col}`: {pct}%")
    else:
        lines.append("- none")

    lines.extend(["", "## Leakage Risk Columns", ""])
    if leakage_risk_columns:
        for col in leakage_risk_columns:
            lines.append(f"- `{col}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "- EDA outputs are descriptive.",
            "- Any preprocessing rule used for modeling should be checked again on train folds only.",
            "- `TC:HDL_ratio` is a derived feature from cholesterol and HDL.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved EDA findings summary: {md_path}")


def main():
    # main() ทำให้ไฟล์นี้ import ฟังก์ชันไปใช้ต่อได้โดยไม่รัน EDA ทันที
    # เมื่อต้องการรันทั้ง workflow ให้เรียกไฟล์นี้โดยตรงจาก terminal
    clean_output_dir()
    df = load_input_data()
    df = add_target_column(df)

    # แสดงขนาดข้อมูลและตัวอย่าง 5 แถวแรก เพื่อเช็กว่าอ่านข้อมูลเข้ามาถูกไฟล์และถูก schema
    print("Shape of data:", df.shape)
    print("\nFirst 5 rows:")
    print(df.head())

    # ตรวจสอบ data type ของแต่ละ column เช่น int, float, object, datetime
    print("\nData Types:")
    print(df.dtypes)

    # ดูสถิติพื้นฐานของ numeric columns เช่น count, mean, std, min, quartile และ max
    print("\nStatistical Summary:")
    print(df.describe())

    # นับจำนวน missing value ในแต่ละ column เพื่อประเมินคุณภาพข้อมูลก่อนสร้าง model/วิเคราะห์ต่อ
    print("\nMissing Values:")
    print(df.isnull().sum())

    # บันทึกตารางสรุปที่ใช้ต่อในรายงานหรือ presentation ได้ง่ายกว่าการอ่านจาก console
    save_eda_summary_tables(df)
    save_outlier_summary(df)

    # สร้างกราฟ EDA หลักทั้งหมด
    plot_missing_values_heatmap(df)
    plot_missing_percent(df)
    plot_feature_distributions(df)
    plot_correlation_matrix(df)
    plot_boxplots(df)
    plot_pairplot(df)
    plot_target_analysis(df)
    patient_target_summary = plot_patient_level_target_analysis()
    plot_age_vs_tc_hdl_ratio(df)
    write_eda_findings_summary(df, patient_target_summary)


if __name__ == "__main__":
    main()
