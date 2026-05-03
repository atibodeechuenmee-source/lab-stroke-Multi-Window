# Paper Notes

โฟลเดอร์นี้ใช้เก็บสรุปงานวิจัยที่เกี่ยวข้องกับโปรเจกต์ stroke และการวิเคราะห์ข้อมูลผู้ป่วย โดยแต่ละงานวิจัยควรมีลิงก์อ้างอิงชัดเจน เพื่อให้ย้อนกลับไปอ่านต้นฉบับได้

## วิธีใช้โฟลเดอร์นี้

- สร้างไฟล์ `.md` แยกตามงานวิจัยแต่ละเรื่อง
- ตั้งชื่อไฟล์ให้อ่านง่าย เช่น `stroke-risk-prediction.md`
- ใส่ลิงก์อ้างอิงของ paper ทุกครั้ง
- สรุปเฉพาะประเด็นที่เกี่ยวข้องกับโปรเจกต์ เช่น dataset, method, features, target, model, metrics และข้อจำกัด

## รายการสรุปงานวิจัย

- [Accurate Prediction of Stroke for Hypertensive Patients Based on Medical Big Data and Machine Learning Algorithms](stroke-prediction-hypertensive-patients-2021.md) - งานวิจัยปี 2021 เรื่องการทำนาย stroke ภายใน 3 ปีในผู้ป่วย hypertension ด้วย electronic medical records และ machine learning

เมื่อเพิ่ม paper ใหม่ ให้เพิ่มรายการในรูปแบบนี้:

```markdown
- [ชื่อ paper](ชื่อไฟล์.md) - หัวข้อ/ประเด็นหลักของ paper
```

## รูปแบบสรุปที่แนะนำ

ใช้ template จากไฟล์:

```text
paper/TEMPLATE.md
```

หัวข้อหลักที่ควรมี:

- ข้อมูลอ้างอิง
- ลิงก์ paper
- วัตถุประสงค์ของงานวิจัย
- Dataset ที่ใช้
- วิธีการหรือ model ที่ใช้
- Features สำคัญ
- Target/outcome
- Evaluation metrics
- ผลลัพธ์สำคัญ
- ข้อจำกัดของงานวิจัย
- สิ่งที่นำมาใช้กับโปรเจกต์ของเราได้
