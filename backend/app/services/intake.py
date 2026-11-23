import hashlib
import io
import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import IntakeState
from app.domain.models import ScheduleIntake
from app.domain.schemas import ParsedSchedule

THAI_MONTH_NAMES = {
    "มกราคม": 1, "ม.ค.": 1, "มค": 1,
    "กุมภาพันธ์": 2, "ก.พ.": 2, "กพ": 2,
    "มีนาคม": 3, "มี.ค.": 3, "มีค": 3,
    "เมษายน": 4, "เม.ย.": 4, "เมย": 4,
    "พฤษภาคม": 5, "พ.ค.": 5, "พค": 5,
    "มิถุนายน": 6, "มิ.ย.": 6, "มิย": 6,
    "กรกฎาคม": 7, "ก.ค.": 7, "กค": 7,
    "สิงหาคม": 8, "ส.ค.": 8, "สค": 8,
    "กันยายน": 9, "ก.ย.": 9, "กย": 9,
    "ตุลาคม": 10, "ต.ค.": 10, "ตค": 10,
    "พฤศจิกายน": 11, "พ.ย.": 11, "พย": 11,
    "ธันวาคม": 12, "ธ.ค.": 12, "ธค": 12,
}


def normalize_year(year: int) -> int:
    if year >= 2400:
        return year - 543
    if year < 100:
        return year + (2000 if year < 70 else 1900)
    return year


def parse_thai_date(text: str, received_at: datetime) -> tuple[date | None, bool]:
    bangkok = received_at.astimezone(ZoneInfo("Asia/Bangkok"))
    if "พรุ่งนี้" in text:
        return (bangkok + timedelta(days=1)).date(), False
    numeric = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?!\d)", text)
    if numeric:
        day, month, year = map(int, numeric.groups())
        try:
            return date(normalize_year(year), month, day), False
        except ValueError:
            return None, True
    month_pattern = "|".join(sorted((re.escape(name) for name in THAI_MONTH_NAMES), key=len, reverse=True))
    named = re.search(rf"(?<!\d)(\d{{1,2}})\s*({month_pattern})\s*(\d{{2,4}})(?!\d)", text)
    if named:
        day, month_name, year = named.groups()
        try:
            return date(normalize_year(int(year)), THAI_MONTH_NAMES[month_name], int(day)), False
        except ValueError:
            return None, True
    return None, True


def parse_line_text(text: str, received_at: datetime) -> ParsedSchedule:
    proposed_date, ambiguous = parse_thai_date(text, received_at)
    hospital_match = re.search(r"(?:โรงพยาบาล|รพ\.?)[\s]*([^,\n]+?)(?=\s+(?:เครื่อง|Chiller|ชิลเลอร์|ตรวจ|เข้า)|$)", text, re.I)
    equipment_match = re.search(r"(?:เครื่อง\s*)?((?:Chiller|ชิลเลอร์)[\s\wก-๙.-]*)", text, re.I)
    errors = []
    if proposed_date is None:
        errors.append("ไม่สามารถระบุวันนัดได้อย่างชัดเจน")
    if hospital_match is None:
        errors.append("ไม่สามารถระบุโรงพยาบาลได้")
    if equipment_match is None:
        errors.append("ไม่สามารถระบุอุปกรณ์ได้")
    return ParsedSchedule(
        proposed_date=proposed_date,
        hospital_text=hospital_match.group(1).strip() if hospital_match else None,
        equipment_text=equipment_match.group(1).strip() if equipment_match else None,
        notes=text,
        ambiguous=ambiguous or bool(errors),
        errors=errors,
    )


def create_text_intake(db: Session, event_id: str, text: str, received_at: datetime) -> ScheduleIntake:
    existing = db.scalar(select(ScheduleIntake).where(ScheduleIntake.source_event_id == event_id))
    if existing:
        return existing
    parsed = parse_line_text(text, received_at)
    intake = ScheduleIntake(
        source_type="LINE_TEXT",
        source_event_id=event_id,
        source_checksum=hashlib.sha256(text.encode()).hexdigest(),
        raw_text=text,
        parsed_data=parsed.model_dump(mode="json"),
        state=IntakeState.NEEDS_REVIEW if parsed.ambiguous else IntakeState.PARSED,
        validation_errors=parsed.errors,
    )
    db.add(intake)
    db.flush()
    return intake


def parse_excel(content: bytes, column_mapping: dict[str, str] | None = None) -> list[ParsedSchedule]:
    mapping = column_mapping or {
        "date": "Date", "hospital": "Hospital", "equipment": "Equipment",
        "technician": "Technician", "notes": "Notes",
    }
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [str(value).strip() if value is not None else "" for value in next(rows)]
    except StopIteration:
        return []
    index = {header: position for position, header in enumerate(headers)}
    missing = [column for column in (mapping["date"], mapping["hospital"], mapping["equipment"]) if column not in index]
    if missing:
        raise ValueError(f"ไม่พบคอลัมน์ที่จำเป็น: {', '.join(missing)}")
    parsed_rows = []
    for row in rows:
        if not any(value is not None for value in row):
            continue
        raw_date = row[index[mapping["date"]]]
        proposed_date = raw_date.date() if isinstance(raw_date, datetime) else raw_date if isinstance(raw_date, date) else None
        if proposed_date is None and raw_date:
            proposed_date, _ = parse_thai_date(str(raw_date), datetime.now(UTC))
        hospital = row[index[mapping["hospital"]]]
        equipment = row[index[mapping["equipment"]]]
        errors = []
        if proposed_date is None:
            errors.append("วันที่ไม่ถูกต้อง")
        if not hospital:
            errors.append("ไม่พบโรงพยาบาล")
        if not equipment:
            errors.append("ไม่พบอุปกรณ์")
        parsed_rows.append(ParsedSchedule(
            proposed_date=proposed_date,
            hospital_text=str(hospital).strip() if hospital else None,
            equipment_text=str(equipment).strip() if equipment else None,
            technician_text=str(row[index[mapping["technician"]]]).strip() if mapping.get("technician") in index and row[index[mapping["technician"]]] else None,
            notes=str(row[index[mapping["notes"]]]).strip() if mapping.get("notes") in index and row[index[mapping["notes"]]] else None,
            ambiguous=bool(errors),
            errors=errors,
        ))
    return parsed_rows

