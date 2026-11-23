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


def create(path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
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

