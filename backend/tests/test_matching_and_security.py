import base64
import hashlib
import hmac

from app.integrations.line import build_flex_message, verify_signature
from app.services.matching import circular_month_distance, normalize_name


def test_hospital_normalization() -> None:
    assert normalize_name(" รพ. กรุงเทพ-เหนือ ") == normalize_name("โรงพยาบาลกรุงเทพ เหนือ")


def test_circular_month_distance() -> None:
    assert circular_month_distance(12, 1) == 1
    assert circular_month_distance(10, 1) == 3


def test_line_signature_validation() -> None:
    body = b'{"events":[]}'
    secret = "secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(body, signature, secret)
    assert not verify_signature(body + b"x", signature, secret)


def test_flex_proposal_contains_confirm_and_reschedule_actions() -> None:
    message = build_flex_message(
        "APPOINTMENT_PROPOSAL",
        {
            "appointment_id": "12345678-1234-1234-1234-123456789012",
            "scheduled_date": "2027-01-15",
            "service_type": "PM",
            "actions": {
                "confirm": "action=confirm&token=one-time-token",
                "reschedule": "action=reschedule&token=one-time-token",
            },
        },
    )
    assert message["type"] == "flex"
    buttons = message["contents"]["footer"]["contents"]
    assert [button["action"]["label"] for button in buttons] == ["ยืนยันนัดหมาย", "ขอเลื่อนนัด"]


def test_technician_change_flex_only_offers_reschedule() -> None:
    message = build_flex_message(
        "TECHNICIAN_DATE_CHANGE",
        {
            "appointment_id": "12345678-1234-1234-1234-123456789012",
            "scheduled_date": "2027-01-20",
            "service_type": "PM",
            "actions": {
                "confirm": "action=confirm&token=token",
                "reschedule": "action=reschedule&token=token",
            },
        },
    )
    buttons = message["contents"]["footer"]["contents"]
    assert [button["action"]["label"] for button in buttons] == ["ขอเลื่อนนัด"]

