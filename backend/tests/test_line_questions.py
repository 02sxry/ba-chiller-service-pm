from app.integrations.line import LineQuestionIntent, build_text_message, parse_line_question


def test_line_question_parser_is_deterministic_for_supported_intents() -> None:
    assert parse_line_question("ช่วยเหลือ") == LineQuestionIntent.HELP
    assert parse_line_question("ขอดูนัดหมายเดือนหน้า") == LineQuestionIntent.APPOINTMENTS
    assert parse_line_question("สวัสดีครับ") == LineQuestionIntent.UNKNOWN


def test_line_text_message_is_bounded() -> None:
    message = build_text_message("x" * 6000)
    assert message["type"] == "text"
    assert len(message["text"]) == 5000
