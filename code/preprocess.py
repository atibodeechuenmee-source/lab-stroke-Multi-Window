# =========================
# 1. Import Libraries
# =========================
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ตั้งค่า style ของกราฟ
sns.set(style="whitegrid")

OUTPUT_DIR = Path("output") / "eda_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PAIRPLOT_MAX_ROWS = 1000
PAIRPLOT_MAX_COLUMNS = 8


def safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def save_current_plot(filename):
    path = OUTPUT_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {path}")

# =========================
# 2. Load Data
# =========================
# อ่านไฟล์ Excel (เปลี่ยน path ตามไฟล์คุณ)
df = pd.read_excel("patients_with_tc_hdl_ratio_with_drugflag.xlsx")

# ดูข้อมูลเบื้องต้น
print("Shape of data:", df.shape)
print("\nFirst 5 rows:")
print(df.head())

# =========================
# 3. ตรวจสอบข้อมูลเบื้องต้น
# =========================

# ดู type ของแต่ละ column
print("\nData Types:")
print(df.dtypes)

# ดูสถิติพื้นฐาน
print("\nStatistical Summary:")
print(df.describe())

# =========================
# 4. ตรวจสอบ Missing Values
# =========================
print("\nMissing Values:")
print(df.isnull().sum())

# Visualize missing values
plt.figure(figsize=(10,5))
sns.heatmap(df.isnull(), cbar=False, cmap="viridis")
plt.title("Missing Values Heatmap")
save_current_plot("missing_values_heatmap.png")

# =========================
# 5. Distribution ของแต่ละ Feature
# =========================
df.hist(figsize=(12,10))
plt.suptitle("Feature Distributions")
save_current_plot("feature_distributions.png")

# =========================
# 6. Correlation Analysis
# =========================
plt.figure(figsize=(10,8))
corr = df.corr(numeric_only=True)

sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Correlation Matrix")
save_current_plot("correlation_matrix.png")

# =========================
# 7. Boxplot (ดู Outliers)
# =========================
for col in df.select_dtypes(include=np.number).columns:
    plt.figure(figsize=(6,4))
    sns.boxplot(x=df[col])
    plt.title(f"Boxplot of {col}")
    save_current_plot(f"boxplot_{safe_filename(col)}.png")

# =========================
# 8. Pairplot (ดูความสัมพันธ์)
# =========================
pairplot_data = df.select_dtypes(include=np.number).iloc[:, :PAIRPLOT_MAX_COLUMNS]
if len(pairplot_data) > PAIRPLOT_MAX_ROWS:
    pairplot_data = pairplot_data.sample(PAIRPLOT_MAX_ROWS, random_state=42)
pairplot = sns.pairplot(pairplot_data)
pairplot.savefig(OUTPUT_DIR / "pairplot.png", dpi=300, bbox_inches="tight")
plt.close(pairplot.fig)
print(f"Saved plot: {OUTPUT_DIR / 'pairplot.png'}")

# =========================
# 9. วิเคราะห์ Target (ถ้ามี drugflag)
# =========================
if 'drugflag' in df.columns:
    plt.figure(figsize=(6,4))
    sns.countplot(x='drugflag', data=df)
    plt.title("Distribution of Drug Flag")
    save_current_plot("drugflag_distribution.png")

    # ดูค่าเฉลี่ยแต่ละ feature แยกตาม drugflag
    print("\nMean values grouped by drugflag:")
    print(df.groupby('drugflag').mean(numeric_only=True))

# =========================
# 10. Scatter Plot Example
# =========================
# เปลี่ยนชื่อ column ตาม dataset จริง
if 'tc_hdl_ratio' in df.columns and 'age' in df.columns:
    plt.figure(figsize=(6,4))
    sns.scatterplot(x='age', y='tc_hdl_ratio', hue='drugflag', data=df)
    plt.title("Age vs TC/HDL Ratio")
    save_current_plot("age_vs_tc_hdl_ratio.png")
