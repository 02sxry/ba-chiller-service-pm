from datetime import UTC, date, datetime
from io import BytesIO

from openpyxl import Workbook

from app.services.intake import parse_excel, parse_line_text, parse_line_texts


def test_parse_buddhist_era_line_message() -> None:
    parsed = parse_line_text(
        "15/01/2570 เข้า PM รพ.A Chiller 1",
        datetime(2026, 11, 23, tzinfo=UTC),
    )
    assert parsed.proposed_date == date(2027, 1, 15)
    assert parsed.hospital_text == "A"
    assert parsed.equipment_text == "Chiller 1"
    assert parsed.ambiguous is False


def test_parse_named_thai_month() -> None:
    parsed = parse_line_text(
        "20 พฤษภาคม 2570 เข้า PM โรงพยาบาล A เครื่อง Chiller 1",
        datetime(2026, 11, 23, tzinfo=UTC),
    )
    assert parsed.proposed_date == date(2027, 5, 20)
    assert parsed.hospital_text == "A"


def test_relative_date_uses_bangkok_timezone() -> None:
    parsed = parse_line_text(
        "พรุ่งนี้เข้า รพ.B ตรวจ Chiller 2",
        datetime(2026, 11, 23, 18, 30, tzinfo=UTC),
    )
    assert parsed.proposed_date == date(2026, 11, 25)


def test_parse_easy_technician_pattern_without_year() -> None:
    parsed = parse_line_text(
        "ขอนแก่น Xstrahl # 26/12",
        datetime(2026, 11, 27, tzinfo=UTC),
    )
    assert parsed.proposed_date == date(2026, 12, 26)
    assert parsed.hospital_text == "ขอนแก่น"
    assert parsed.equipment_text == "Xstrahl"
    assert parsed.ambiguous is False


def test_parse_compact_technician_pattern_without_hash_or_space() -> None:
    parsed = parse_line_text(
        "ขอนแก่นXstrahl 26/12",
        datetime(2026, 11, 27, tzinfo=UTC),
    )
    assert parsed.proposed_date == date(2026, 12, 26)
    assert parsed.hospital_text == "ขอนแก่น"
    assert parsed.equipment_text == "Xstrahl"
    assert parsed.ambiguous is False


def test_parse_multiple_easy_technician_rows() -> None:
    parsed = parse_line_texts(
        "ขอนแก่น Xstrahl # 26/12\nอุบล IX, Hal # 13/12\nรามา Hal > เพิ่งเข้าเดือน 10\nธรรมศาสตร์ Chiller # 5/12",
        datetime(2026, 11, 27, tzinfo=UTC),
    )
    assert [(row.hospital_text, row.equipment_text, row.proposed_date) for row in parsed] == [
        ("ขอนแก่น", "Xstrahl", date(2026, 12, 26)),
        ("อุบล", "IX, Hal", date(2026, 12, 13)),
        ("รามา", "Hal", None),
        ("ธรรมศาสตร์", "Chiller", date(2026, 12, 5)),
    ]
    assert parsed[2].ambiguous is True
    assert "ไม่สามารถระบุวันนัดได้อย่างชัดเจน" in parsed[2].errors


def test_excel_parser_reports_row_errors() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Date", "Hospital", "Equipment", "Technician", "Notes"])
    sheet.append([datetime(2027, 1, 15), "รพ. A", "Chiller 1", "ช่างหนึ่ง", "PM"])
    sheet.append(["ไม่ใช่วันที่", "", "Chiller 2", None, None])
    buffer = BytesIO()
    workbook.save(buffer)
    rows = parse_excel(buffer.getvalue())
    assert rows[0].proposed_date == date(2027, 1, 15)
    assert rows[0].ambiguous is False
    assert rows[1].ambiguous is True
    assert "วันที่ไม่ถูกต้อง" in rows[1].errors

