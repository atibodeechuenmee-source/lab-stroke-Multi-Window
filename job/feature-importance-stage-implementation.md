# งาน: Implement Stage 07 Feature Importance

## เป้าหมาย

สร้างโค้ดจาก `docs/pipeline/07-feature-importance.md` เพื่อประเมินความสำคัญของฟีเจอร์ temporal และเปรียบเทียบวิธีลดมิติ 3 แบบตาม paper:

- ANOVA F-test
- PCA
- ANOVA + PCA

พร้อมกำหนดเงื่อนไขกัน leakage ให้ทุกขั้นตอน fit เฉพาะ training fold ใน cross-validation

## ไฟล์โค้ดที่สร้าง

- `src/feature_importance.py`

## สิ่งที่โค้ดทำ

`src/feature_importance.py` เป็นโมดูล/CLI ของ Stage 07 โดยทำงานดังนี้:

- โหลด Extract Set 1/2/3 จาก Stage 05 (`output/feature_engineering_output`)
- โหลด model context จาก Stage 06 (`output/model_output/modeling_report.json`) เพื่อแนบในรายงาน
- เตรียม feature matrix เฉพาะ numerical columns และ target `stroke`
- เลือก CV strategy แบบ patient-level ตามความพร้อมของ class:
  - `LOOCV` เมื่อข้อมูลมีขนาดเล็กและ class เพียงพอ
  - `StratifiedKFold` เมื่อข้อมูลมากขึ้น
  - skip เมื่อมี class เดียวหรือ minority class < 2
- ประเมิน 3 วิธี:
  - ANOVA: ทดลอง `top-k` หลายค่า (default: 5, 10, 15, 20, 30, 40, 50)
  - PCA: ทดลองจำนวน components หลายค่า (default: 2, 3, 5, 8, 10, 15, 20, 30)
  - ANOVA+PCA: เลือก top-k ก่อน แล้วทำ PCA บน selected features
- ใช้ Logistic Regression (`class_weight="balanced"`) เป็นตัวประเมินทุกวิธี
- คำนวณ metrics หลัก: `sensitivity`, `specificity`, `G-Mean`
- สร้าง ANOVA ranking (F-score และ p-value)
- สร้างสรุป best configuration ต่อ extract set

## Leakage Guard ที่ implement

- `SimpleImputer`, `StandardScaler`, `SelectKBest`, `PCA` และ classifier ถูก fit ภายในแต่ละ training fold เท่านั้น
- ไม่ใช้ test fold ในการคำนวณ feature selection หรือ PCA parameters
- metric ประเมินจาก out-of-fold predictions

## วิธีรัน

ค่า default:

```powershell
.\.venv\Scripts\python.exe -m src.feature_importance
```

ระบุ path เอง:

```powershell
.\.venv\Scripts\python.exe -m src.feature_importance --feature-dir output/feature_engineering_output --model-dir output/model_output --output-dir output/feature_importance_output
```

## Output

โฟลเดอร์ default:

```text
output/feature_importance_output
```

ไฟล์ที่สร้าง:

- `feature_importance_summary.csv`
- `anova_feature_ranking.csv`
- `anova_performance.csv`
- `pca_performance.csv`
- `anova_pca_performance.csv`
- `best_feature_importance_choices.csv`
- `feature_importance_report.json`
- `feature_importance_report.md`

## ผลการรันล่าสุด

รันด้วย:

```powershell
.\.venv\Scripts\python.exe -m src.feature_importance
```

ผลสรุป:

- `sets_seen`: extract_set_1, extract_set_2, extract_set_3
- `sets_completed`: 0
- `sets_skipped`: 3

เหตุผลเชิงข้อมูล: temporal cohort ที่ผ่านเกณฑ์ strict completeness มีขนาดเล็กมาก และ class distribution ไม่พอสำหรับการทำ CV (สอดคล้องกับผล Stage 06 ที่ temporal sets ถูก skip ด้วยเหตุผลเดียวกัน)

## Acceptance Criteria

- มีการทดสอบทั้ง ANOVA, PCA, ANOVA+PCA ในโค้ดครบตาม pipeline
- มี fold-level leakage guard ครบใน feature selection และ PCA
- มีผลลัพธ์แยกตาราง performance ต่อวิธี
- มีรายงานสรุป best configuration ต่อ extract set เมื่อข้อมูลเพียงพอ
- รองรับกรณีข้อมูลไม่พอโดย `skip_reason` ชัดเจน

## สถานะ

Implemented แล้วใน `src/feature_importance.py` และรันสร้าง artifacts ได้สำเร็จ
