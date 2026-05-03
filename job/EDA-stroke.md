# EDA Stroke

เอกสารนี้อธิบายขั้นตอนการทำ Exploratory Data Analysis (EDA) ของชุดข้อมูลผู้ป่วย stroke/กลุ่มเสี่ยง stroke ในโปรเจกต์นี้ โดยอ้างอิงจากสคริปต์ `code/preprocess.py` และผลลัพธ์กราฟที่บันทึกไว้ในโฟลเดอร์ `output`

## วัตถุประสงค์ของการทำ EDA

การทำ EDA ในงานนี้มีเป้าหมายหลักเพื่อทำความเข้าใจข้อมูลก่อนนำไปวิเคราะห์หรือสร้างโมเดลต่อ โดยเน้นตรวจสอบประเด็นสำคัญต่อไปนี้:

- ขนาดและโครงสร้างของ dataset
- ชนิดข้อมูลของแต่ละคอลัมน์
- ค่าที่หายไป missing values
- การกระจายของตัวแปรเชิงตัวเลข
- ความสัมพันธ์ระหว่างตัวแปร
- ค่าผิดปกติหรือ outliers
- ความพร้อมของข้อมูลสำหรับงานวิเคราะห์ขั้นต่อไป

## Dataset ที่ใช้

ไฟล์ข้อมูลหลักคือ:

```text
patients_with_tc_hdl_ratio_with_drugflag.xlsx
```

ข้อมูลมีจำนวน:

- 218,772 records
- 30 columns
- ช่วงวันที่ `vstdate` ตั้งแต่ 2014-10-01 ถึง 2024-06-30

ข้อมูลประกอบด้วยตัวแปรกลุ่มหลัก เช่น ข้อมูลผู้ป่วย อายุ เพศ ค่าร่างกาย ความดันโลหิต ผลแล็บ โรคร่วม diagnosis ข้อมูลยา และ flag ที่เกี่ยวข้องกับโรคหรือการใช้ยา

รายละเอียด dataset แบบเต็มอยู่ในไฟล์ `DATASET.md`

## ขั้นตอนที่ 1: Import Libraries

สคริปต์ใช้ library หลักดังนี้:

- `pandas` สำหรับอ่านและจัดการข้อมูลตาราง
- `numpy` สำหรับช่วยจัดการข้อมูลตัวเลข
- `matplotlib` สำหรับสร้างกราฟ
- `seaborn` สำหรับสร้างกราฟเชิงสถิติ
- `pathlib` สำหรับจัดการ path ของโฟลเดอร์ output

มีการตั้งค่า Matplotlib backend เป็น `Agg` เพื่อให้สคริปต์บันทึกกราฟเป็นไฟล์ได้โดยไม่ต้องเปิดหน้าต่างแสดงผล

## ขั้นตอนที่ 2: Load Data

โหลดข้อมูลจากไฟล์ Excel ด้วยคำสั่ง:

```python
df = pd.read_excel("patients_with_tc_hdl_ratio_with_drugflag.xlsx")
```

หลังโหลดข้อมูล สคริปต์พิมพ์ข้อมูลเบื้องต้น เช่น:

- shape ของ dataset
- 5 แถวแรก
- data types ของแต่ละคอลัมน์
- statistical summary

ผลที่ได้คือ dataset มีขนาด `218,772 x 30`

## ขั้นตอนที่ 3: ตรวจสอบ Missing Values

สคริปต์ตรวจสอบ missing values ด้วย:

```python
df.isnull().sum()
```

และสร้างกราฟ heatmap เพื่อดู pattern ของ missing values:

```text
output/missing_values_heatmap.png
```

ข้อสังเกตสำคัญ:

- คอลัมน์พื้นฐาน เช่น `hn`, `vstdate`, `sex`, `age` ไม่มี missing values
- ผลแล็บหลายตัวมี missing values สูง เช่น `FBS`, `Triglyceride`, `LDL`, `TC:HDL_ratio`, `HDL`, `Cholesterol`, `eGFR`, `Creatinine`
- ความดันโลหิต `bps` และ `bpd` มี missing values ประมาณ 12-13%
- ข้อมูลข้อความ เช่น `ComorbidityDiagnosis`, `ตำบล`, `ยาที่ได้รับ` มี missing values ในระดับที่ต้องพิจารณาก่อนใช้งานต่อ

## ขั้นตอนที่ 4: ดู Distribution ของ Features

สคริปต์สร้าง histogram ของตัวแปรเชิงตัวเลขทั้งหมดด้วย:

```python
df.hist(figsize=(12, 10))
```

ผลลัพธ์ถูกบันทึกที่:

```text
output/feature_distributions.png
```

กราฟนี้ใช้ดูการกระจายของข้อมูล เช่น:

- อายุผู้ป่วย
- ส่วนสูง น้ำหนัก BMI
- ความดันโลหิต
- ค่าผลแล็บ
- flag โรคและยา

## ขั้นตอนที่ 5: วิเคราะห์ Correlation

สคริปต์คำนวณ correlation เฉพาะคอลัมน์ตัวเลข:

```python
corr = df.corr(numeric_only=True)
```

และสร้าง heatmap:

```text
output/correlation_matrix.png
```

กราฟนี้ใช้ดูความสัมพันธ์เชิงเส้นระหว่างตัวแปร เช่น ความสัมพันธ์ระหว่างตัวแปรผลแล็บ ความดัน BMI อายุ และ flag ต่าง ๆ

## ขั้นตอนที่ 6: ตรวจ Outliers ด้วย Boxplot

สคริปต์วนทุกคอลัมน์ตัวเลขและสร้าง boxplot แยกไฟล์:

```python
for col in df.select_dtypes(include=np.number).columns:
    sns.boxplot(x=df[col])
```

ผลลัพธ์ถูกบันทึกเป็นไฟล์:

```text
output/boxplot_*.png
```

ตัวอย่างไฟล์:

- `output/boxplot_age.png`
- `output/boxplot_bmi.png`
- `output/boxplot_bps.png`
- `output/boxplot_LDL.png`
- `output/boxplot_TC_HDL_ratio.png`

ข้อสังเกตจาก boxplot:

- บางคอลัมน์มีค่าที่ควรตรวจสอบเพิ่มเติม เช่น `LDL` มีค่าต่ำสุดติดลบ
- ผลแล็บและความดันโลหิตมีช่วงค่ากว้าง จึงควรตรวจ outliers ก่อนนำไปสร้างโมเดล

## ขั้นตอนที่ 7: Pairplot

สคริปต์สร้าง pairplot เพื่อดูความสัมพันธ์ระหว่างตัวแปรตัวเลขบางส่วน:

```text
output/pairplot.png
```

เนื่องจาก dataset มีขนาดใหญ่ จึงจำกัด pairplot ให้ใช้:

- sample 1,000 แถว
- 8 คอลัมน์ตัวเลขแรก

เหตุผลคือ pairplot ของข้อมูลเต็ม 218,772 แถวและตัวแปรตัวเลขจำนวนมากใช้เวลานานเกินไปและไม่เหมาะกับการรันซ้ำ

## ขั้นตอนที่ 8: Target/Flag Analysis

สคริปต์มี logic สำหรับตรวจคอลัมน์ `drugflag` หากมีอยู่ใน dataset:

```python
if 'drugflag' in df.columns:
    sns.countplot(x='drugflag', data=df)
```

แต่ dataset ปัจจุบันไม่มีคอลัมน์ชื่อ `drugflag` โดยตรง จึงไม่ได้สร้างกราฟ `drugflag_distribution.png`

อย่างไรก็ตาม dataset มี flag ที่เกี่ยวข้องกับยาและโรค เช่น:

- `Statin`
- `Gemfibrozil`
- `Antihypertensive_flag`
- `heart_disease`
- `hypertension`
- `diabetes`

## ขั้นตอนที่ 9: Scatter Plot

สคริปต์มี logic สำหรับสร้าง scatter plot ระหว่าง `age` และ `tc_hdl_ratio` หากมีคอลัมน์ตรงตามชื่อ:

```python
if 'tc_hdl_ratio' in df.columns and 'age' in df.columns:
    sns.scatterplot(x='age', y='tc_hdl_ratio', hue='drugflag', data=df)
```

แต่ dataset ปัจจุบันใช้ชื่อคอลัมน์ `TC:HDL_ratio` ไม่ใช่ `tc_hdl_ratio` จึงไม่ได้สร้างกราฟ scatter plot ส่วนนี้

หากต้องการใช้กราฟนี้ต่อ ควรปรับชื่อคอลัมน์ในสคริปต์ให้ตรงกับ dataset ปัจจุบัน

## Output จาก EDA

ผลลัพธ์หลักจาก EDA ถูกเก็บในโฟลเดอร์:

```text
output/
```

ไฟล์สำคัญที่สร้างแล้ว:

- `missing_values_heatmap.png`
- `feature_distributions.png`
- `correlation_matrix.png`
- `pairplot.png`
- `boxplot_*.png`

รวมไฟล์กราฟที่ตรวจสอบแล้วจำนวน 29 ไฟล์

## ข้อสรุปเบื้องต้นจาก EDA

- Dataset มีขนาดใหญ่และมีข้อมูลหลายปี เหมาะสำหรับงานวิเคราะห์เชิงคลินิกหรือ machine learning หากจัดการข้อมูลให้เหมาะสมก่อน
- ตัวแปรพื้นฐานและ flag หลายตัวไม่มี missing values จึงพร้อมใช้งานได้ค่อนข้างดี
- ตัวแปรผลแล็บมี missing values สูงมาก ต้องวางแผนจัดการก่อนนำไปวิเคราะห์หรือสร้างโมเดล
- มีค่าที่ควรตรวจสอบเพิ่มเติม เช่น `LDL` ติดลบ
- ตัวแปรข้อความ เช่น diagnosis และยาที่ได้รับ อาจต้องทำ feature extraction หรือ encoding เพิ่มเติม
- ก่อนสร้างโมเดลต้องกำหนด target variable ให้ชัดเจน และระวัง data leakage จากตัวแปรยา/diagnosis

## งานที่ควรทำต่อ

- ปรับชื่อคอลัมน์ใน scatter plot ให้ตรงกับ `TC:HDL_ratio`
- เพิ่มกราฟวิเคราะห์ flag สำคัญ เช่น `Statin`, `Gemfibrozil`, `Antihypertensive_flag`
- สร้างแผนจัดการ missing values แยกตามกลุ่มตัวแปร
- ตรวจสอบ outliers ของ lab values และ blood pressure อย่างละเอียด
- กำหนด target variable สำหรับงาน machine learning หรือ statistical analysis ขั้นต่อไป
