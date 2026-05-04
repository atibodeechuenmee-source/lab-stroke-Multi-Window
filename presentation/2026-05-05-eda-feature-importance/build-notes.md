# Build Notes

## Tone

- ใช้ภาษาไทยแบบนำเสนอจริง กระชับ และตรงประเด็น
- วาง narrative เป็นสายเดียว: data readiness -> data caveats -> modeling guardrails -> interpretable signals -> limitations
- หลีกเลี่ยงคำพูดที่ทำให้ผู้ฟังเข้าใจว่าโมเดลพร้อมใช้ทางคลินิกทันที

## Visual Style

- ใช้โทน clinical analytics: พื้นหลังสะอาด, contrast สูง, chart อ่านง่าย
- ให้ตัวเลขหลักอยู่เป็น KPI callout ไม่ฝังในย่อหน้ายาว
- ใช้สีเน้นเฉพาะประเด็น risk หรือ caveat เช่น missing values, minority class และ leakage
- กราฟ missingness, correlation, feature importance และ SHAP ควรเป็น visual หลักของเด็ค ไม่ควรแทนด้วยข้อความล้วน

## Caveat ที่ต้องใส่

- **Missing values:** Lab variables หลายตัว missing มากกว่า 70% จึงต้องระวังทั้ง bias และ pattern ของการถูกส่งตรวจ
- **Class imbalance:** Stroke records มี 5,170 จาก 218,772 records หรือ 2.36% ทำให้ accuracy อย่างเดียวไม่พอ ต้องอ่าน precision, recall, F1 และ ROC-AUC ร่วมกัน
- **Leakage:** Target มาจาก `PrincipleDiagnosis` ดังนั้น diagnosis/text fields ต้องไม่ถูกใช้เป็น features
- **Feature importance is not causal effect:** RF importance และ SHAP บอกว่า feature ช่วยโมเดลทำนาย แต่ไม่พิสูจน์ว่า feature เป็นสาเหตุของ stroke

## สิ่งที่ห้ามตีความเกินข้อมูล

- ห้ามสรุปว่า hypertension หรือ diabetes เป็นสาเหตุจากผล feature importance ของโมเดลนี้
- ห้ามบอกว่าโมเดลผ่าน validation สำหรับใช้งานจริง เพราะยังต้องมี temporal validation และ external หรือ prospective validation
- ห้ามใช้ผลจาก `output/model_output/*` ในเด็คนี้
- ห้ามเพิ่มเนื้อหานอกขอบเขต EDA และ feature importance
- ห้ามใช้ diagnosis/text fields เป็นเหตุผลของ feature importance เพราะฟิลด์เหล่านั้นถูกกันออกเพื่อลด leakage

## Next-step Slide Guidance

ในสไลด์สุดท้ายให้เสนอ next steps แบบจำกัด scope:

- Permutation importance เพื่อตรวจ robustness ของ ranking
- Temporal validation เพื่อทดสอบ performance ข้ามเวลา
- Patient-level dataset สำหรับโจทย์ prediction ที่เหมาะกับการใช้งานจริงกว่า record-level analysis
