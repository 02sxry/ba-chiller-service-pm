import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

INPUT_SHEETS = {
    "Hospitals_Input": ["hospital_code", "hospital_name", "short_name", "active", "notes"],
    "Hospital_Aliases_Input": ["hospital_id", "alias"],
    "Manufacturers_Input": ["name", "active"],
    "Equipment_Types_Input": ["name", "active"],
    "Equipment_Input": ["equipment_code", "hospital_id", "manufacturer_id", "equipment_type_id", "equipment_name", "model", "serial_number", "room_location", "active", "notes"],
    "PM_Plans_Input": ["equipment_id", "plan_year", "annual_frequency", "planning_mode", "start_month", "planned_months"],
    "Next_Year_PM_Drafts": ["draft_id", "equipment_id", "target_year", "annual_frequency", "planning_mode", "start_month", "planned_months", "excluded"],
}
VIEW_SHEETS = [
    "Hospitals_View", "Equipment_View", "PM_Slots_View", "Appointments_View",
    "Confirmations_View", "Reschedule_Requests_View", "PM_Yearly_Summary",
    "Sync_Status", "Data_Dictionary",
]
README_ROWS = [
    ["BA CHILLER SERVICE & PM — Google Sheets Template"],
    ["วิธีใช้", "กรอกเฉพาะชีตที่ลงท้ายด้วย _Input แล้วปล่อยให้ระบบสร้างชีต _View ให้อัตโนมัติ"],
    ["แหล่งข้อมูลจริง", "PostgreSQL เป็นแหล่งข้อมูลจริง Google Sheets ใช้กรอกข้อมูลและแสดงผลเท่านั้น"],
    ["พร้อมใช้งานตอนนี้", "Hospitals_Input รองรับการส่งเข้า/ออกระบบแล้ว"],
    ["เตรียมไว้สำหรับขั้นถัดไป", "Equipment_Input, PM_Plans_Input และ Next_Year_PM_Drafts มีโครงสร้างพร้อม แต่ต้องเปิด API sync เพิ่มก่อนใช้จริง"],
    ["ข้อห้าม", "ห้ามแก้ไขชีต _View และห้ามใช้เลขแถวเป็น row_key"],
    ["operation", "ใช้ CREATE สำหรับข้อมูลใหม่, UPDATE สำหรับแก้ไข และ DEACTIVATE สำหรับปิดใช้งาน"],
    ["row_key", "รหัสถาวรของแถว เช่น hospital-001 ห้ามเปลี่ยนหลังส่งข้อมูลแล้ว"],
    ["record_id", "เว้นว่างเมื่อ CREATE; ใช้ UUID เดิมเมื่อ UPDATE หรือ DEACTIVATE"],
    ["expected_version", "เว้นว่างเมื่อ CREATE; ใช้ version ล่าสุดจากชีต _View เมื่อ UPDATE"],
]
CONTROL_COLUMNS = ["row_key", "record_id", "expected_version", "operation"]
RESULT_COLUMNS = ["validation_status", "validation_errors", "processed_at"]


def style_header(sheet) -> None:
    fill = PatternFill("solid", fgColor="0B374C")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, cell in enumerate(sheet[1], 1):
        sheet.column_dimensions[get_column_letter(index)].width = max(16, len(str(cell.value)) + 3)


def create_readme(workbook: Workbook) -> None:
    sheet = workbook.create_sheet("เริ่มที่นี่", 0)
    for row in README_ROWS:
        sheet.append(row)
    sheet["A1"].fill = PatternFill("solid", fgColor="0B374C")
    sheet["A1"].font = Font(color="FFFFFF", bold=True, size=14)
    sheet.merge_cells("A1:B1")
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 110
    sheet.freeze_panes = "A2"
    for row in range(2, sheet.max_row + 1):
        sheet.cell(row, 1).font = Font(bold=True, color="0B374C")
        sheet.cell(row, 2).alignment = sheet.cell(row, 2).alignment.copy(wrap_text=True)


def create(path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    create_readme(workbook)
    for name, business_columns in INPUT_SHEETS.items():
        sheet = workbook.create_sheet(name)
        sheet.append(CONTROL_COLUMNS + business_columns + RESULT_COLUMNS)
        style_header(sheet)
    for name in VIEW_SHEETS:
        sheet = workbook.create_sheet(name)
        sheet.append(["generated_at", "ข้อมูลใน worksheet นี้สร้างจาก PostgreSQL และเป็น read-only"])
        style_header(sheet)
        sheet.protection.sheet = True
    dictionary = workbook["Data_Dictionary"]
    dictionary.protection.sheet = False
    dictionary.delete_rows(1, dictionary.max_row)
    dictionary.append(["field", "description"])
    dictionary.append(["row_key", "รหัสถาวรของแถว ห้ามใช้เลขลำดับแถว"])
    dictionary.append(["record_id", "UUID ของ record ใน PostgreSQL"])
    dictionary.append(["expected_version", "version ที่ผู้ใช้เห็น ใช้ตรวจ optimistic concurrency"])
    dictionary.append(["operation", "CREATE, UPDATE หรือ DEACTIVATE ตามสิทธิ์"])
    style_header(dictionary)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "BA_CHILLER_PM_MASTER.xlsx")
    create(output)
    print(output)

