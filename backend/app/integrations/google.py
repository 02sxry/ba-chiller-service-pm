from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class GoogleResult:
    success: bool
    reference_id: str | None = None
    error: str | None = None


class GoogleWorkspaceProvider(Protocol):
    def export_rows(self, worksheet: str, rows: list[dict[str, Any]]) -> GoogleResult: ...
    def store_file(self, folder_kind: str, name: str, content: bytes) -> GoogleResult: ...


class MockGoogleWorkspaceProvider:
    def export_rows(self, worksheet: str, rows: list[dict[str, Any]]) -> GoogleResult:
        return GoogleResult(True, reference_id=f"mock-sheet:{worksheet}:{len(rows)}")

    def store_file(self, folder_kind: str, name: str, content: bytes) -> GoogleResult:
        return GoogleResult(True, reference_id=f"mock-drive:{folder_kind}:{name}:{len(content)}")

