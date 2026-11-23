from typing import Any, Protocol


class IntentProvider(Protocol):
    def extract(self, text: str) -> dict[str, Any]: ...


class DisabledGeminiProvider:
    def extract(self, text: str) -> dict[str, Any]:
        return {"available": False, "intent": None, "parameters": {}, "source": "deterministic_fallback"}

