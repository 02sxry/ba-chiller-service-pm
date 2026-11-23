import json
from typing import Any, Protocol

import httpx

from app.core.config import Settings


class IntentProvider(Protocol):
    def extract(self, text: str) -> dict[str, Any]: ...


class DisabledGeminiProvider:
    def extract(self, text: str) -> dict[str, Any]:
        return {"available": False, "intent": None, "parameters": {}, "source": "deterministic_fallback"}


class GeminiProvider:
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        if not settings.gemini_api_key:
            raise ValueError("ต้องกำหนด GEMINI_API_KEY เมื่อเปิด Gemini provider")
        self.api_key = settings.gemini_api_key
        self.client = client or httpx.Client(timeout=15.0)

    def extract(self, text: str) -> dict[str, Any]:
        instruction = (
            "แยก intent จากข้อความภาษาไทยของระบบนัดหมาย PM เท่านั้น "
            "ตอบเป็น JSON object เดียวรูปแบบ {intent:string|null,parameters:object}. "
            "ห้ามสร้าง SQL ห้ามอนุมัตินัด ห้ามอ้างว่างานเสร็จ และห้ามเติมข้อมูลที่ไม่มีในข้อความ. "
            f"ข้อความ: {text[:2000]}"
        )
        try:
            response = self.client.post(
                self.endpoint,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": instruction}]}],
                    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
                },
            )
            response.raise_for_status()
            candidates = response.json().get("candidates", [])
            generated = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
            parsed = json.loads(generated)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("parameters", {}), dict):
                raise ValueError("Gemini output schema invalid")
            return {
                "available": True,
                "intent": parsed.get("intent"),
                "parameters": parsed.get("parameters", {}),
                "source": "gemini",
            }
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return {"available": False, "intent": None, "parameters": {}, "source": "deterministic_fallback"}


def build_intent_provider(settings: Settings) -> IntentProvider:
    return GeminiProvider(settings) if settings.gemini_api_key else DisabledGeminiProvider()

