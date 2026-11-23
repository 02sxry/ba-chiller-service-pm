from app.core.config import Settings
from app.integrations.gemini import DisabledGeminiProvider, GeminiProvider, build_intent_provider


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_gemini_defaults_to_disabled() -> None:
    assert isinstance(build_intent_provider(Settings()), DisabledGeminiProvider)


def test_gemini_validates_json_contract() -> None:
    client = FakeClient(FakeResponse({"candidates": [{"content": {"parts": [{"text": '{"intent":"APPOINTMENTS","parameters":{"year":2026}}'}]}}]}))
    result = GeminiProvider(Settings(gemini_api_key="key"), client=client).extract("ขอดูนัดหมาย")
    assert result == {"available": True, "intent": "APPOINTMENTS", "parameters": {"year": 2026}, "source": "gemini"}
    assert client.calls[0][1]["params"] == {"key": "key"}


def test_gemini_invalid_response_uses_safe_fallback() -> None:
    client = FakeClient(FakeResponse({"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}))
    result = GeminiProvider(Settings(gemini_api_key="key"), client=client).extract("ข้อความ")
    assert result["available"] is False
    assert result["source"] == "deterministic_fallback"
