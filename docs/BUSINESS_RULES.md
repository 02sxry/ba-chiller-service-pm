# กฎธุรกิจ

1. หนึ่งอุปกรณ์มี active annual plan ได้ไม่เกินหนึ่งแผนต่อ `plan_year`
2. PM Slot เกิดหลัง Admin อนุมัติแผนเท่านั้น วันนัดไม่ใช่ตัวตนของ Slot
3. Slot หนึ่งมี active appointment ปัจจุบันได้หนึ่งรายการ และมี revision ย้อนหลังได้หลายรายการ
4. `planned_month`, `plan_year` และ `scheduled_date` เป็นคนละข้อมูล นัดข้ามปีไม่ย้ายภาระไปปีใหม่
5. `CONFIRMED` เป็นหลักฐานการยอมรับวันนัด ไม่ใช่หลักฐานการทำงาน
6. ระบบไม่มี `COMPLETED`, actual visit หรือการคำนวณงานเสร็จคงเหลือ
7. ชื่อโรงพยาบาลที่ไม่แน่ชัดสร้าง Draft และรอ Admin พิจารณา
8. อุปกรณ์ที่ไม่รู้จักห้ามเดาผู้ผลิต รุ่น serial number หรือ equipment code
9. นัดจากช่างต้องผ่าน Admin ก่อนแจ้งโรงพยาบาล
10. Hospital LINE group อ่านและตอบเฉพาะข้อมูลโรงพยาบาลที่ map ไว้
11. Technician change หลัง confirmation ต้องผ่าน Admin คง confirmation revision เดิม และแจ้งวันใหม่โดยไม่บังคับ Confirm ซ้ำ
12. Provider accepted หมายถึงผู้ให้บริการรับคำขอ ไม่ได้แปลว่าผู้รับอ่านแล้ว
13. Spreadsheet ใช้ stable row key และ expected version ไม่มี last-write-wins
14. Google หรือ LINE outage ต้องไม่ย้อนสถานะธุรกิจที่ commit แล้ว

