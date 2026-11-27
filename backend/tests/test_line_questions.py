from app.integrations.line import LineQuestionIntent, build_flex_message, build_text_message, parse_line_question


def test_line_question_parser_is_deterministic_for_supported_intents() -> None:
    assert parse_line_question("ช่วยเหลือ") == LineQuestionIntent.HELP
    assert parse_line_question("ขอดูนัดหมายเดือนหน้า") == LineQuestionIntent.APPOINTMENTS
    assert parse_line_question("สวัสดีครับ") == LineQuestionIntent.UNKNOWN


def test_pm_proposal_uses_short_formal_thai_message() -> None:
    message = build_flex_message(
        "APPOINTMENT_PROPOSAL",
        {
            "appointment_id": "12345678-0000-0000-0000-000000000000",
            "scheduled_date": "2026-12-19",
            "service_type": "PM",
            "equipment_name": "Chiller",
            "room_location": "ตึก 72 ปี",
            "actions": {},
        },
    )
    contents = message["contents"]["body"]["contents"]
    rendered = "\n".join(item["text"] for item in contents)
    assert "ขออนุญาตแจ้งวันเข้า PM Chiller" in rendered
    assert "ตึก 72 ปี - 19/12/69" in rendered
    assert "ไม่ทราบว่าสะดวกไหมครับ" in rendered


def test_line_text_message_is_bounded() -> None:
    message = build_text_message("x" * 6000)
    assert message["type"] == "text"
    assert len(message["text"]) == 5000
