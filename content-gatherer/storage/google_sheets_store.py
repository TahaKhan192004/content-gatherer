"""
Google Sheets Storage — append processed content to a spreadsheet tab.
Auth via GOOGLE_CREDS_JSON + GOOGLE_TOKEN_JSON env vars (GitHub Secrets or .env).
"""
import json
import logging
import os
from datetime import date

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import (
    GOOGLE_CREDS_JSON,
    GOOGLE_SHEETS_ENABLED,
    GOOGLE_SPREADSHEET_ID,
    GOOGLE_TOKEN_JSON,
    GOOGLE_WORKSHEET_NAME,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _quote_sheet_name(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def _load_credentials() -> Credentials:
    if not GOOGLE_CREDS_JSON:
        raise ValueError("GOOGLE_CREDS_JSON environment variable is not set")
    if not GOOGLE_TOKEN_JSON:
        raise ValueError("GOOGLE_TOKEN_JSON environment variable is not set")

    creds = Credentials.from_authorized_user_info(
        json.loads(GOOGLE_TOKEN_JSON), SCOPES
    )

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        return creds

    if os.getenv("GITHUB_ACTIONS"):
        raise ValueError(
            "Google token is invalid and could not be refreshed. "
            "Update GOOGLE_TOKEN_JSON secret with a fresh token.json."
        )

    client_config = json.loads(GOOGLE_CREDS_JSON)
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    logger.warning(
        "Google token was re-authenticated via browser. "
        "Update GOOGLE_TOKEN_JSON with the new token JSON."
    )
    return creds


def get_sheets_service():
    """Build an authenticated Google Sheets API client from env secrets."""
    creds = _load_credentials()
    return build("sheets", "v4", credentials=creds)


def _item_to_row(item: dict, run_date: str) -> list:
    source = item.get("source_name") or item.get("source_type") or ""
    categories = item.get("categories") or []
    if isinstance(categories, list):
        categories_text = ", ".join(str(c) for c in categories)
    else:
        categories_text = str(categories)

    return [
        source,
        item.get("title", "")[:500],
        item.get("url", ""),
        item.get("relevance_score", 0),
        categories_text,
        item.get("summary", "")[:3000],
        item.get("published_at") or "",
        run_date,
    ]


def store_content_to_sheet(items: list[dict], *, run_date: str | None = None) -> int:
    """
    Append processed content items to the configured worksheet.
    Returns the number of rows appended.
    """
    if not GOOGLE_SHEETS_ENABLED:
        logger.info("Google Sheets export disabled — skipping")
        return 0

    if not items:
        logger.info("No items to append to Google Sheets")
        return 0

    run_date = run_date or date.today().isoformat()
    rows = [_item_to_row(item, run_date) for item in items]

    service = get_sheets_service()
    worksheet = _quote_sheet_name(GOOGLE_WORKSHEET_NAME)
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=GOOGLE_SPREADSHEET_ID,
            range=f"{worksheet}!A:H",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        )
        .execute()
    )

    appended = int(result.get("updates", {}).get("updatedRows", 0))
    logger.info(
        f"Appended {appended}/{len(items)} rows to Google Sheet "
        f"({GOOGLE_WORKSHEET_NAME})"
    )
    return appended


def is_sheets_configured() -> bool:
    """True when Sheets export is enabled and both OAuth secrets are set."""
    return (
        GOOGLE_SHEETS_ENABLED
        and bool(GOOGLE_CREDS_JSON.strip())
        and bool(GOOGLE_TOKEN_JSON.strip())
    )
