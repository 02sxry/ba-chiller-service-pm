import base64
import hashlib
import hmac
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import httpx

from app.core.config import Settings


def verify_signature(raw_body: bytes, signature: str, channel_secret: str) -> bool:
    digest = hmac.new(channel_secret.encode(), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


@dataclass
class ProviderResult:
    accepted: bool
    provider_message_id: str | None = None
    error: str | None = None


class LineQuestionIntent(StrEnum):
    HELP = "HELP"
    APPOINTMENTS = "APPOINTMENTS"
    UNKNOWN = "UNKNOWN"


def parse_line_question(text: str) -> LineQuestionIntent:
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return LineQuestionIntent.UNKNOWN
    if any(keyword in normalized for keyword in ("ช่วยเหลือ", "เมนู", "คำสั่ง", "help")):
        return LineQuestionIntent.HELP
    if any(keyword in normalized for keyword in ("นัด", "วันไหน", "กำหนดการ", "appointment", "schedule")):
        return LineQuestionIntent.APPOINTMENTS
    return LineQuestionIntent.UNKNOWN


class LineProvider(Protocol):
    def push(self, destination_id: str, payload: dict[str, Any]) -> ProviderResult: ...


class MockLineProvider:
    def push(self, destination_id: str, payload: dict[str, Any]) -> ProviderResult:
        digest = hashlib.sha256(f"{destination_id}:{payload}".encode()).hexdigest()[:20]
        return ProviderResult(accepted=True, provider_message_id=f"mock-{digest}")


class LineMessagingApiProvider:
    """Opt-in LINE push adapter; no network call is made by the mock provider."""

    endpoint = "https://api.line.me/v2/bot/message/push"

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        if not settings.line_channel_access_token:
            raise ValueError("ต้องกำหนด LINE_CHANNEL_ACCESS_TOKEN เมื่อเปิด LINE provider")
        self.access_token = settings.line_channel_access_token
        self.client = client or httpx.Client(timeout=10.0)

    def push(self, destination_id: str, payload: dict[str, Any]) -> ProviderResult:
        try:
            response = self.client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"to": destination_id, "messages": [payload]},
            )
            if 200 <= response.status_code < 300:
                return ProviderResult(accepted=True)
            return ProviderResult(False, error=f"LINE API HTTP {response.status_code}: {response.text[:300]}")
        except httpx.HTTPError as exc:
            return ProviderResult(False, error=f"LINE API request failed: {type(exc).__name__}: {exc}")


def build_line_provider(settings: Settings) -> LineProvider:
    if not settings.line_channel_access_token:
        return MockLineProvider()
    return LineMessagingApiProvider(settings)


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


def build_text_message(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text[:5000]}

