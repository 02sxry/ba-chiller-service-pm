from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.integrations.google import GoogleApiWorkspaceProvider, MockGoogleWorkspaceProvider, build_google_provider


def test_google_provider_defaults_to_mock() -> None:
    provider = build_google_provider(Settings())
    assert isinstance(provider, MockGoogleWorkspaceProvider)


def test_real_provider_requires_workspace_configuration() -> None:
    with pytest.raises(ValueError, match="GOOGLE_SPREADSHEET_ID"):
        GoogleApiWorkspaceProvider(Settings(google_use_real_provider=True))


def test_real_provider_exports_rows_through_sheets_service() -> None:
    class Values:
        def get(self, **kwargs):
            self.get_kwargs = kwargs
            return SimpleNamespace(execute=lambda: {"values": [["row_key", "record_id", "active"], ["hospital:h1", "h1", False]]})

        def update(self, **kwargs):
            self.update_kwargs = kwargs
            return SimpleNamespace(execute=lambda: {"updatedRange": kwargs["range"]})

        def append(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(execute=lambda: {"updates": {"updatedRange": "Hospitals_View!A1:B2"}})

    class Spreadsheets:
        def __init__(self):
            self.values_api = Values()

        def values(self):
            return self.values_api

    sheets = Spreadsheets()
    provider = GoogleApiWorkspaceProvider(
        Settings(google_spreadsheet_id="sheet-1", google_drive_root_folder_id="folder-1"),
        sheets_service=SimpleNamespace(spreadsheets=lambda: sheets),
        drive_service=SimpleNamespace(),
    )
    result = provider.export_rows("Hospitals_View", [{"row_key": "hospital:h1", "record_id": "h1", "active": True}])
    assert result.success is True
    assert result.reference_id == "sheets:Hospitals_View:update:2"
    assert sheets.values_api.get_kwargs["spreadsheetId"] == "sheet-1"
    assert sheets.values_api.update_kwargs["range"] == "Hospitals_View!A2:C2"


def test_drive_upload_rejects_missing_named_folder() -> None:
    class Files:
        def list(self, **kwargs):
            self.query = kwargs["q"]
            return SimpleNamespace(execute=lambda: {"files": []})

    class Media:
        def create(self, **kwargs):
            raise AssertionError("ไม่ควร upload เมื่อไม่พบโฟลเดอร์")

    provider = GoogleApiWorkspaceProvider(
        Settings(google_spreadsheet_id="sheet-1", google_drive_root_folder_id="folder-1"),
        sheets_service=SimpleNamespace(),
        drive_service=SimpleNamespace(files=lambda: Files()),
    )
    result = provider.store_file("generated_reports", "report.xlsx", b"data")
    assert result.success is False
    assert "ไม่พบโฟลเดอร์" in result.error
