from types import SimpleNamespace

from app.core.config import Settings
from app.integrations.line import LineMessagingApiProvider, MockLineProvider, ProviderResult, build_line_provider


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_line_provider_defaults_to_mock_without_token() -> None:
    assert isinstance(build_line_provider(Settings()), MockLineProvider)


def test_line_provider_posts_authorized_payload() -> None:
    client = FakeClient(SimpleNamespace(status_code=200, text=""))
    provider = LineMessagingApiProvider(Settings(line_channel_access_token="token"), client=client)
    result = provider.push("group-1", {"type": "text", "text": "ทดสอบ"})
    assert result == ProviderResult(accepted=True)
    assert client.calls[0][1]["headers"]["Authorization"] == "Bearer token"
    assert client.calls[0][1]["json"]["to"] == "group-1"


def test_line_provider_returns_safe_error_for_api_failure() -> None:
    client = FakeClient(SimpleNamespace(status_code=429, text="rate limited"))
    result = LineMessagingApiProvider(Settings(line_channel_access_token="token"), client=client).push("group-1", {})
    assert result.accepted is False
    assert "429" in result.error
