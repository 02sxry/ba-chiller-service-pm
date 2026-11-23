import base64
import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Protocol


def verify_signature(raw_body: bytes, signature: str, channel_secret: str) -> bool:
    digest = hmac.new(channel_secret.encode(), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


@dataclass
class ProviderResult:
    accepted: bool
    provider_message_id: str | None = None
    error: str | None = None


class LineProvider(Protocol):
    def push(self, destination_id: str, payload: dict[str, Any]) -> ProviderResult: ...


class MockLineProvider:
    def push(self, destination_id: str, payload: dict[str, Any]) -> ProviderResult:
        digest = hashlib.sha256(f"{destination_id}:{payload}".encode()).hexdigest()[:20]
        return ProviderResult(accepted=True, provider_message_id=f"mock-{digest}")


def build_flex_message(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    date_text = payload["scheduled_date"]
    action_data = payload.get("actions") or {}
    title = "ข้อเสนอนัดหมาย PM" if kind == "APPOINTMENT_PROPOSAL" else "แจ้งเปลี่ยนวันนัดหมาย"
    body_contents: list[dict[str, Any]] = [
        {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": "#0D756D"},
        {"type": "text", "text": f"วันที่นัด: {date_text}", "margin": "md", "wrap": True},
        {"type": "text", "text": f"ประเภทบริการ: {payload.get('service_type', 'PM')}", "size": "sm", "color": "#667788"},
        {"type": "text", "text": f"อ้างอิง: {payload['appointment_id'][:8].upper()}", "size": "xs", "color": "#8899AA", "margin": "md"},
    ]
    buttons: list[dict[str, Any]] = []
    if kind == "APPOINTMENT_PROPOSAL" and action_data.get("confirm"):
        buttons.append({
            "type": "button",
            "style": "primary",
            "color": "#0D756D",
            "action": {"type": "postback", "label": "ยืนยันนัดหมาย", "data": action_data["confirm"], "displayText": "ยืนยันนัดหมาย"},
        })
    if action_data.get("reschedule"):
        buttons.append({
            "type": "button",
            "action": {"type": "postback", "label": "ขอเลื่อนนัด", "data": action_data["reschedule"], "displayText": "ขอเลื่อนนัด"},
        })
    bubble: dict[str, Any] = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": body_contents},
    }
    if buttons:
        bubble["footer"] = {"type": "box", "layout": "vertical", "spacing": "sm", "contents": buttons}
    return {"type": "flex", "altText": f"{title} วันที่ {date_text}", "contents": bubble}

