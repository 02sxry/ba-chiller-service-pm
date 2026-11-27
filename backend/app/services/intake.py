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


def _short_pattern_year(year_text: str) -> int:
    # In the technician shorthand, two digits denote an abbreviated Buddhist year.
    return int(year_text) + 1957 if len(year_text) == 2 else normalize_year(int(year_text))


def _infer_year(day: int, month: int, received_at: datetime) -> int:
    """Infer the next upcoming year for shorthand dates without a year."""
    bangkok_date = received_at.astimezone(ZoneInfo("Asia/Bangkok")).date()
    year = bangkok_date.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        return year
    return year + 1 if candidate < bangkok_date else year


def parse_thai_date(
    text: str, received_at: datetime, *, technician_shorthand: bool = False,
) -> tuple[date | None, bool]:
    bangkok = received_at.astimezone(ZoneInfo("Asia/Bangkok"))
    if "พรุ่งนี้" in text:
        return (bangkok + timedelta(days=1)).date(), False
    numeric = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?(?!\d)", text)
    if numeric:
        day_text, month_text, year_text = numeric.groups()
        day, month = int(day_text), int(month_text)
        if year_text:
            year = _short_pattern_year(year_text) if technician_shorthand else normalize_year(int(year_text))
        else:
            year = _infer_year(day, month, received_at)
        try:
            return date(year, month, day), False
        except ValueError:
            return None, True
    month_pattern = "|".join(sorted((re.escape(name) for name in THAI_MONTH_NAMES), key=len, reverse=True))
    named = re.search(rf"(?<!\d)(\d{{1,2}})\s*({month_pattern})(?:\s*(\d{{2,4}}))?(?!\d)", text)
    if named:
        day_text, month_name, year_text = named.groups()
        day = int(day_text)
        month = THAI_MONTH_NAMES[month_name]
        if year_text:
            year = _short_pattern_year(year_text) if technician_shorthand else normalize_year(int(year_text))
        else:
            year = _infer_year(day, month, received_at)
        try:
            return date(year, month, day), False
        except ValueError:
            return None, True
    return None, True


def _parse_technician_short_line(text: str, received_at: datetime) -> ParsedSchedule | None:
    """Parse the easy technician pattern: ``Hospital Equipment # date``."""
    match = re.match(r"^\s*(?P<details>[^#\n]+?)\s*#\s*(?P<date>[^#\n]+?)\s*$", text)
    if not match:
        return None

    details = " ".join(match.group("details").split())
    date_text = match.group("date").strip()
    if "|" in details:
        hospital_text, equipment_text = (part.strip() for part in details.split("|", 1))
    else:
        parts = details.split(None, 1)
        hospital_text = parts[0] if parts else None
        equipment_text = parts[1].strip() if len(parts) == 2 else None
    hospital_text = re.sub(r"^(?:โรงพยาบาล|รพ\.?)[\s]*", "", hospital_text or "", flags=re.IGNORECASE).strip()
    proposed_date, ambiguous_date = parse_thai_date(date_text, received_at, technician_shorthand=True)
    errors: list[str] = []
    if not proposed_date:
        errors.append("ไม่สามารถระบุวันนัดได้อย่างชัดเจน")
    if not hospital_text:
        errors.append("ไม่สามารถระบุโรงพยาบาลได้")
    if not equipment_text:
        errors.append("ไม่สามารถระบุอุปกรณ์ได้")
    return ParsedSchedule(
        proposed_date=proposed_date,
        hospital_text=hospital_text or None,
        equipment_text=equipment_text or None,
        notes=text.strip(),
        ambiguous=ambiguous_date or bool(errors),
        errors=errors,
    )


def _parse_technician_note_line(text: str) -> ParsedSchedule | None:
    """Parse a technician row that reports a month/note but no exact date."""
    match = re.match(r"^\s*(?P<details>[^>\n]+?)\s*>\s*(?P<note>.+?)\s*$", text)
    if not match:
        return None
    details = " ".join(match.group("details").split())
    if "|" in details:
        hospital_text, equipment_text = (part.strip() for part in details.split("|", 1))
    else:
        parts = details.split(None, 1)
        hospital_text = parts[0] if parts else None
        equipment_text = parts[1].strip() if len(parts) == 2 else None
    hospital_text = re.sub(r"^(?:โรงพยาบาล|รพ\.?)[\s]*", "", hospital_text or "", flags=re.IGNORECASE).strip()
    errors = ["ไม่สามารถระบุวันนัดได้อย่างชัดเจน"]
    if not hospital_text:
        errors.append("ไม่สามารถระบุโรงพยาบาลได้")
    if not equipment_text:
        errors.append("ไม่สามารถระบุอุปกรณ์ได้")
    return ParsedSchedule(
        hospital_text=hospital_text or None,
        equipment_text=equipment_text or None,
        notes=f"{text.strip()} ({match.group('note').strip()})",
        ambiguous=True,
        errors=errors,
    )


def _parse_technician_compact_line(text: str, received_at: datetime) -> ParsedSchedule | None:
    """Parse ``ขอนแก่นXstrahl 26/12`` without a hash or separating space."""
    date_match = re.search(r"(?<!\d)(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s*$", text)
    if not date_match:
        return None
    details = text[:date_match.start()].strip()
    match = re.match(
        r"^(?P<hospital>[ก-๙][ก-๙\s.]*?)(?P<equipment>[A-Za-z][A-Za-z0-9,._/\- ]*)$",
        details,
    )
    if not match:
        return None
    hospital_text = re.sub(r"^(?:โรงพยาบาล|รพ\.?)[\s]*", "", match.group("hospital").strip(), flags=re.IGNORECASE).strip()
    equipment_text = match.group("equipment").strip()
    proposed_date, ambiguous_date = parse_thai_date(date_match.group(1), received_at, technician_shorthand=True)
    errors: list[str] = []
    if not proposed_date:
        errors.append("ไม่สามารถระบุวันนัดได้อย่างชัดเจน")
    return ParsedSchedule(
        proposed_date=proposed_date,
        hospital_text=hospital_text or None,
        equipment_text=equipment_text or None,
        notes=text.strip(),
        ambiguous=ambiguous_date or not hospital_text or not equipment_text,
        errors=errors,
    )


def parse_line_text(text: str, received_at: datetime) -> ParsedSchedule:
    short_line = _parse_technician_short_line(text, received_at)
    if short_line:
        return short_line
    note_line = _parse_technician_note_line(text)
    if note_line:
        return note_line
    compact_line = _parse_technician_compact_line(text, received_at)
    if compact_line:
        return compact_line
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


def parse_line_texts(text: str, received_at: datetime) -> list[ParsedSchedule]:
    """Parse one or more technician rows while preserving the original text."""
    lines = [re.sub(r"^[-•]\s+", "", line.strip()) for line in text.splitlines() if line.strip()]
    if any("#" in line or ">" in line or _parse_technician_compact_line(line, received_at) for line in lines):
        return [parse_line_text(line, received_at) for line in lines]
    return [parse_line_text(text, received_at)]


def create_text_intake(db: Session, event_id: str, text: str, received_at: datetime) -> ScheduleIntake:
    existing = db.scalar(select(ScheduleIntake).where(ScheduleIntake.source_event_id == event_id))
    if existing:
        return existing
    parsed_rows = parse_line_texts(text, received_at)
    parsed = parsed_rows[0]
    parsed_data = parsed.model_dump(mode="json") if len(parsed_rows) == 1 else {
        "pattern": "TECHNICIAN_SHORT_LIST",
        "items": [row.model_dump(mode="json") for row in parsed_rows],
    }
    if len(parsed_rows) == 1:
        errors = parsed.errors
    else:
        errors = [
            f"รายการที่ {index}: {error}"
            for index, row in enumerate(parsed_rows, 1)
            for error in row.errors
        ]
    intake = ScheduleIntake(
        source_type="LINE_TEXT",
        source_event_id=event_id,
        source_checksum=hashlib.sha256(text.encode()).hexdigest(),
        raw_text=text,
        parsed_data=parsed_data,
        state=IntakeState.NEEDS_REVIEW if any(row.ambiguous for row in parsed_rows) else IntakeState.PARSED,
        validation_errors=errors,
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

