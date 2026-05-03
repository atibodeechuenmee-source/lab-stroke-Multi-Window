# Worklog

ไฟล์นี้ใช้บันทึกและอธิบายงานที่ทำในโปรเจกต์นี้ เมื่อมีการอัปเดตโค้ดหรือเปลี่ยนขั้นตอนการทำงาน ให้เพิ่มรายละเอียดต่อท้ายในส่วน "ประวัติการอัปเดต"

## ภาพรวมโปรเจกต์

โปรเจกต์นี้ใช้สำหรับสำรวจและวิเคราะห์ข้อมูลผู้ป่วยจากไฟล์ Excel `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx` ผ่านสคริปต์ `src/preprocess.py`

สคริปต์หลักทำงานดังนี้:

- อ่านข้อมูลจากไฟล์ Excel
- แสดงข้อมูลเบื้องต้น เช่น shape, head, data types, summary statistics และ missing values
- สร้างกราฟสำหรับตรวจสอบข้อมูล เช่น missing values heatmap, distribution, correlation, boxplot และ pairplot
- บันทึกกราฟทั้งหมดเป็นไฟล์ภาพ `.png` ลงในโฟลเดอร์ `output/eda_output`

## โครงสร้างไฟล์สำคัญ

- `src/preprocess.py` - สคริปต์หลักสำหรับอ่านข้อมูล วิเคราะห์เบื้องต้น และสร้างกราฟ
- `src/feature_importance.py` - สคริปต์สำหรับ modeling, feature importance, SHAP และ model comparison
- `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx` - ไฟล์ข้อมูลต้นทาง
- `output/eda_output/` - โฟลเดอร์เก็บไฟล์กราฟจาก EDA
- `output/feature_importance_output/` - โฟลเดอร์เก็บผลลัพธ์จาก feature importance
- `.venv/` - virtual environment สำหรับรัน Python และ dependency ของโปรเจกต์

## วิธีรัน

รันจากโฟลเดอร์หลักของโปรเจกต์:

```powershell
.\.venv\Scripts\python.exe .\src\preprocess.py
```

หลังรันเสร็จ กราฟจะถูกบันทึกไว้ในโฟลเดอร์ `output`

## ประวัติการอัปเดต

### 2026-05-03

ปรับโครงสร้างโปรเจกต์

- สร้างโฟลเดอร์ `data/raw`, `data/interim`, `data/processed`, `src`, `notebooks` และ `tests`
- ย้ายไฟล์ข้อมูลหลักจาก root ไป `data/raw/patients_with_tc_hdl_ratio_with_drugflag.xlsx`
- ย้ายสคริปต์จาก `code/` ไป `src/`
- ย้ายสำเนา Excel ที่เคยอยู่ใน `code/` ไป `data/raw/patients_with_tc_hdl_ratio_with_drugflag_code_copy.xlsx` เพื่อเก็บไว้ก่อน ไม่ลบข้อมูลที่อาจต่างกัน
- เพิ่ม `src/__init__.py` และ `.gitkeep` สำหรับโฟลเดอร์ว่างที่ต้องการ track
- ปรับ path ใน `src/preprocess.py` และ `src/feature_importance.py` ให้ชี้ไปที่ `data/raw/`
- อัปเดต `README.md`, `DATASET.md`, `job/EDA-stroke.md` และ `job/feature-importance-stroke.md` ให้ตรงกับโครงสร้างใหม่

แยกโฟลเดอร์ผลลัพธ์ใน `output`

- สร้าง `output/eda_output` สำหรับผลลัพธ์จาก EDA
- สร้าง `output/feature_importance_output` สำหรับผลลัพธ์จาก feature importance
- ปรับ `src/preprocess.py` ให้บันทึกกราฟ EDA ลง `output/eda_output`
- ปรับ `src/feature_importance.py` ให้บันทึกตาราง กราฟ และ metrics ลง `output/feature_importance_output`
- ย้ายไฟล์ output เดิมไปยังโฟลเดอร์ย่อยตามประเภทงาน
- อัปเดตเอกสารให้ชี้ path output ใหม่

เพิ่มงาน `feature importance`

- เพิ่มสคริปต์ `src/feature_importance.py`
- สร้าง target `stroke_flag` จากรหัส ICD-10 กลุ่ม `I60-I69*` ใน `PrincipleDiagnosis` เท่านั้น
- ใช้ Random Forest แบบ class-balanced เพื่อคำนวณ feature importance
- บันทึกผลลัพธ์เป็น `output/feature_importance_output/feature_importance_stroke.csv`, `output/feature_importance_output/feature_importance_stroke.png` และ `output/feature_importance_output/feature_importance_stroke_metrics.txt`
- เพิ่มเอกสาร `job/feature-importance-stroke.md` เพื่ออธิบายวิธีทำ ผลลัพธ์ และข้อควรระวัง
- ติดตั้ง dependency `scikit-learn` ใน `.venv`
- เพิ่ม `requirements.txt` เพื่อระบุ dependency ที่ใช้ในโปรเจกต์
- เพิ่ม SHAP analysis ทั้ง global summary, SHAP bar และ local waterfall plot
- เพิ่ม Stratified K-Fold Cross Validation สำหรับเปรียบเทียบความเสถียรของโมเดล
- เพิ่ม XGBoost เพื่อเปรียบเทียบกับ RandomForest
- ปรับ RandomForest `min_samples_leaf` จาก 20 เป็น 5 เพื่อลด over-smoothing
- เพิ่มไฟล์ output สำหรับ `model_cv_metrics`, `model_holdout_metrics`, `feature_importance_model_comparison` และ `shap_*`
- เพิ่มคอมเมนต์และ docstring ภาษาไทยอย่างละเอียดใน `src/feature_importance.py` เพื่ออธิบาย workflow, target, preprocessing, cross-validation, model comparison และ SHAP

เพิ่มสรุปงานวิจัยในโฟลเดอร์ `paper`

- อ่านและสรุป paper เรื่องการทำนาย stroke ในผู้ป่วย hypertension ด้วย medical big data และ machine learning
- เพิ่มไฟล์ `paper/stroke-prediction-hypertensive-patients-2021.md`
- เพิ่มลิงก์อ้างอิง paper, PubMed และ DOI
- สรุป dataset, target, features, methods, metrics, results, limitations และสิ่งที่นำมาใช้กับโปรเจกต์ของเราได้
- อัปเดตรายการ paper ใน `paper/README.md`

เพิ่มโฟลเดอร์ `paper`

- ใช้เก็บสรุปงานวิจัยที่อ่านและเกี่ยวข้องกับโปรเจกต์
- เพิ่ม `paper/README.md` เพื่ออธิบายวิธีจัดเก็บและรายการ paper ที่สรุปแล้ว
- เพิ่ม `paper/TEMPLATE.md` เป็น template สำหรับสรุป paper แต่ละเรื่อง
- กำหนดให้แต่ละสรุปต้องมีลิงก์อ้างอิง เช่น DOI, URL ของ paper, dataset หรือ code ถ้ามี

เพิ่มไฟล์ `job/EDA-stroke.md`

- สร้างโฟลเดอร์ `job` สำหรับเก็บเอกสารงานเฉพาะหัวข้อ
- เพิ่มเอกสารอธิบายขั้นตอนการทำ EDA ของโปรเจกต์
- อธิบายวัตถุประสงค์ของ EDA, dataset ที่ใช้, ขั้นตอนตรวจ missing values, distribution, correlation, boxplot และ pairplot
- สรุป output ที่ได้จากโฟลเดอร์ `output`
- เพิ่มข้อสรุปเบื้องต้นจาก EDA และงานที่ควรทำต่อ

เพิ่มไฟล์ `DATASET.md`

- ใช้เป็นเอกสารอธิบาย dataset หลังทำ EDA
- ระบุจำนวนแถว คอลัมน์ ช่วงวันที่ และกลุ่มตัวแปรใน dataset
- เพิ่ม data dictionary สำหรับคอลัมน์ทั้ง 30 คอลัมน์
- เพิ่มตาราง missing values พร้อมเปอร์เซ็นต์
- เพิ่มค่าสรุปเบื้องต้นของตัวแปรสำคัญ เช่น อายุ ความดัน ไขมัน ผลแล็บ และค่าไต
- เพิ่มข้อสังเกตจาก EDA และแนวทางใช้งาน dataset ต่อ

เพิ่มไฟล์ `README.md`

- ใช้เป็นไฟล์อธิบายภาพรวมของโปรเจกต์
- ระบุว่าโปรเจกต์ทำอะไร ใช้ข้อมูลไฟล์ไหน และสร้างผลลัพธ์อะไร
- เพิ่มวิธีรันสคริปต์ `src/preprocess.py`
- อธิบายความแตกต่างระหว่าง `README.md` กับ `WORKLOG.md`

ปรับการสร้างกราฟใน `src/preprocess.py`

- เปลี่ยนจากการเรียก `plt.show()` เป็นการบันทึกไฟล์ภาพลงโฟลเดอร์ `output`
- เพิ่ม helper `save_current_plot()` เพื่อบันทึกกราฟซ้ำ ๆ ด้วยรูปแบบเดียวกัน
- เพิ่ม `safe_filename()` เพื่อแปลงชื่อคอลัมน์ให้ใช้เป็นชื่อไฟล์ได้ปลอดภัย
- ตั้งค่า Matplotlib backend เป็น `Agg` เพื่อให้สร้างไฟล์ภาพได้โดยไม่ต้องเปิดหน้าต่างกราฟ
- ตั้งค่า stdout เป็น UTF-8 เพื่อให้พิมพ์ชื่อคอลัมน์ภาษาไทยใน console ได้
- จำกัด `pairplot` ให้ใช้ sample 1,000 แถว และ 8 คอลัมน์แรก เพื่อให้สคริปต์รันจบได้จริงกับข้อมูลขนาดใหญ่

ผลลัพธ์ที่ตรวจสอบแล้ว:

- สคริปต์รันสำเร็จ
- มีไฟล์กราฟถูกสร้างใน `output/eda_output` จำนวน 29 ไฟล์
- ตัวอย่างไฟล์ที่ได้: `missing_values_heatmap.png`, `feature_distributions.png`, `correlation_matrix.png`, `pairplot.png`, `boxplot_*.png`

หมายเหตุ:

- ระหว่างรันมี warning เรื่องฟอนต์ Arial ไม่รองรับ glyph ภาษาไทยบางตัวในกราฟ แต่ไม่ทำให้สคริปต์ล้มและไม่กระทบการสร้างไฟล์ภาพ
