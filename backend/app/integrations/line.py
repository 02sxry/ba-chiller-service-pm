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

