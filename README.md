# Stroke Patient Data Exploration

โปรเจกต์นี้ใช้สำหรับสำรวจข้อมูลผู้ป่วย วิเคราะห์ EDA และสร้างโมเดลเบื้องต้นสำหรับงาน Stroke prediction จากข้อมูล clinical tabular data

## โปรเจกต์นี้ทำอะไร

- อ่านข้อมูลผู้ป่วยจากไฟล์ Excel ใน `data/raw/`
- ทำ EDA เพื่อตรวจสอบ missing values, distribution, correlation และ outliers
- สร้าง target `stroke_flag` จาก `PrincipleDiagnosis` โดยใช้ ICD-10 ช่วง `I60-I69*`
- สร้างโมเดล RandomForest และ XGBoost เพื่อเปรียบเทียบผล
- วิเคราะห์ feature importance และ SHAP explainability
- บันทึกผลลัพธ์ทั้งหมดไว้ใน `output/`

## ข้อมูลที่ใช้

ไฟล์ข้อมูลหลัก:

```text
data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx
```

หมายเหตุ: มีไฟล์ `data/raw/patients_with_tc_hdl_ratio_with_drugflag_code_copy.xlsx` เป็นสำเนาที่เคยอยู่ในโฟลเดอร์ `code/` จึงเก็บแยกไว้ก่อนเพื่อไม่ลบข้อมูลที่อาจต่างกัน

## วิธีรัน

ติดตั้ง dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

รัน EDA:

```powershell
.\.venv\Scripts\python.exe .\src\eda.py
```

รัน feature importance / modeling / SHAP:

```powershell
.\.venv\Scripts\python.exe .\src\feature_importance.py
```

รัน patient-level 3-month stroke prediction:

```powershell
.\.venv\Scripts\python.exe .\src\patient_level_prediction.py
```

## Output

ผลลัพธ์ถูกแยกตามประเภทงาน:

```text
output/
├── eda_output/
├── feature_importance_output/
└── model_output/
```

ตัวอย่างไฟล์ EDA:

- `output/eda_output/missing_values_heatmap.png`
- `output/eda_output/feature_distributions.png`
- `output/eda_output/correlation_matrix.png`
- `output/eda_output/pairplot.png`
- `output/eda_output/boxplot_*.png`

ตัวอย่างไฟล์ modeling / explainability:

- `output/feature_importance_output/feature_importance_stroke.csv`
- `output/feature_importance_output/feature_importance_model_comparison.png`
- `output/feature_importance_output/model_cv_metrics.csv`
- `output/feature_importance_output/model_holdout_metrics.csv`
- `output/feature_importance_output/shap_summary_random_forest.png`
- `output/feature_importance_output/shap_local_positive_random_forest.png`

ตัวอย่างไฟล์ patient-level prediction:

- `data/processed/patient_level_90d_stroke.csv`
- `output/model_output/patient_level_90d_model_report.txt`
- `output/model_output/patient_level_90d_holdout_metrics.csv`
- `output/model_output/patient_level_90d_shap_summary_*.png`

## โครงสร้างโปรเจกต์

```text
.
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── src/
│   ├── __init__.py
│   ├── eda.py
│   ├── feature_importance.py
│   └── patient_level_prediction.py
├── notebooks/
├── output/
│   ├── eda_output/
│   ├── feature_importance_output/
│   └── model_output/
├── job/
│   ├── EDA-stroke.md
│   ├── feature-importance-stroke.md
│   └── patient-level-3month-stroke-prediction.md
├── paper/
│   ├── README.md
│   ├── TEMPLATE.md
│   └── stroke-prediction-hypertensive-patients-2021.md
├── tests/
├── DATASET.md
├── README.md
├── requirements.txt
└── WORKLOG.md
```

## บทบาทของแต่ละโฟลเดอร์

- `data/raw/` - ข้อมูลต้นฉบับที่ไม่ควรแก้โดยตรง
- `data/interim/` - ข้อมูลที่ผ่านการแปลงหรือ cleaning บางส่วน
- `data/processed/` - ข้อมูลพร้อมใช้สำหรับ modeling
- `src/` - source code หลักที่รันซ้ำได้
- `notebooks/` - notebook สำหรับทดลองหรือสำรวจไอเดีย
- `output/` - กราฟ ตาราง metrics และผลลัพธ์จากสคริปต์
- `job/` - เอกสารอธิบายงานที่ทำ เช่น EDA และ feature importance
- `paper/` - สรุปงานวิจัยและลิงก์อ้างอิง
- `tests/` - พื้นที่สำหรับ unit tests หรือ validation scripts

## ไฟล์เอกสาร

- `DATASET.md` - อธิบาย dataset, data dictionary, missing values และข้อสังเกตจาก EDA
- `job/EDA-stroke.md` - อธิบายขั้นตอนการทำ EDA
- `job/feature-importance-stroke.md` - อธิบาย feature importance, model comparison และ SHAP
- `job/patient-level-3month-stroke-prediction.md` - อธิบาย cohort และโมเดล patient-level 90-day prediction
- `paper/` - เก็บสรุปงานวิจัยที่อ่าน
- `WORKLOG.md` - บันทึกประวัติการอัปเดตงาน
