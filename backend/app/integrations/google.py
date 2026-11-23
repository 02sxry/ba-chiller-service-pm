from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings


def _column_label(index: int) -> str:
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


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


class GoogleApiWorkspaceProvider:
    """Google Sheets/Drive adapter, enabled explicitly and loaded lazily.

    Keeping imports lazy lets local development and tests run without Google SDKs
    or credentials. The database remains authoritative; this adapter only
    exports projections and stores source files.
    """

    def __init__(self, settings: Settings, *, sheets_service: Any = None, drive_service: Any = None) -> None:
        if not settings.google_spreadsheet_id or not settings.google_drive_root_folder_id:
            raise ValueError("ต้องกำหนด GOOGLE_SPREADSHEET_ID และ GOOGLE_DRIVE_ROOT_FOLDER_ID")
        if sheets_service is None or drive_service is None:
            if not settings.google_service_account_file:
                raise ValueError("ต้องกำหนด GOOGLE_SERVICE_ACCOUNT_FILE เมื่อเปิด Google provider")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
            except ImportError as exc:
                raise RuntimeError("ยังไม่ได้ติดตั้ง Google API SDK สำหรับ production adapter") from exc
            credentials = service_account.Credentials.from_service_account_file(
                settings.google_service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive.file",
                ],
            )
            sheets_service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
            drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.spreadsheet_id = settings.google_spreadsheet_id
        self.drive_root_folder_id = settings.google_drive_root_folder_id
        self.sheets = sheets_service
        self.drive = drive_service

    def export_rows(self, worksheet: str, rows: list[dict[str, Any]]) -> GoogleResult:
        if not rows:
            return GoogleResult(True, reference_id=f"sheets:{self.spreadsheet_id}:{worksheet}:empty")
        columns = list(rows[0])
        values = [[row.get(column) for column in columns] for row in rows]
        try:
            values_api = self.sheets.spreadsheets().values()
            existing = values_api.get(
                spreadsheetId=self.spreadsheet_id, range=f"{worksheet}!A:ZZ"
            ).execute().get("values", [])
            if not existing:
                response = values_api.append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{worksheet}!A1",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [columns, *values]},
                ).execute()
                return GoogleResult(True, reference_id=response.get("updates", {}).get("updatedRange", worksheet))

            header = existing[0]
            key_column = "row_key" if "row_key" in header else "record_id"
            if key_column not in header:
                return GoogleResult(False, error=f"Google Sheets worksheet {worksheet} ไม่มีคอลัมน์ {key_column}")
            key_index = header.index(key_column)
            indexes = {name: header.index(name) for name in columns if name in header}
            references = []
            for row in rows:
                ordered = [None] * len(header)
                for name, index in indexes.items():
                    ordered[index] = row.get(name)
                key = str(row.get(key_column) or "")
                matching_row = next((position for position, existing_row in enumerate(existing[1:], start=2)
                                     if len(existing_row) > key_index and str(existing_row[key_index]) == key), None)
                if matching_row is None:
                    values_api.append(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{worksheet}!A1",
                        valueInputOption="RAW",
                        insertDataOption="INSERT_ROWS",
                        body={"values": [ordered]},
                    ).execute()
                    references.append(f"append:{key}")
                else:
                    end_column = _column_label(len(header))
                    values_api.update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{worksheet}!A{matching_row}:{end_column}{matching_row}",
                        valueInputOption="RAW",
                        body={"values": [ordered]},
                    ).execute()
                    references.append(f"update:{matching_row}")
            return GoogleResult(True, reference_id=f"sheets:{worksheet}:{','.join(references)}")
        except Exception as exc:
            return GoogleResult(False, error=f"Google Sheets export failed: {type(exc).__name__}: {exc}")

    def store_file(self, folder_kind: str, name: str, content: bytes) -> GoogleResult:
        from io import BytesIO

        try:
            from googleapiclient.http import MediaIoBaseUpload

            metadata = {"name": name, "parents": [self.drive_root_folder_id], "description": f"BA Chiller/{folder_kind}"}
            media = MediaIoBaseUpload(BytesIO(content), mimetype="application/octet-stream", resumable=False)
            response = self.drive.files().create(body=metadata, media_body=media, fields="id,name").execute()
            return GoogleResult(True, reference_id=response["id"])
        except Exception as exc:
            return GoogleResult(False, error=f"Google Drive upload failed: {type(exc).__name__}: {exc}")


def build_google_provider(settings: Settings) -> GoogleWorkspaceProvider:
    if not settings.google_use_real_provider:
        return MockGoogleWorkspaceProvider()
    return GoogleApiWorkspaceProvider(settings)

