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
    result = provider.export_rows("Hospitals_View", [{"record_id": "h1", "active": True}])
    assert result.success is True
    assert result.reference_id == "Hospitals_View!A1:B2"
    assert sheets.values_api.kwargs["spreadsheetId"] == "sheet-1"
