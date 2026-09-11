from __future__ import annotations

from pathlib import Path

from app.config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_TOKEN_FILE

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service(token_file: Path | None = None):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = token_file or GOOGLE_TOKEN_FILE
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError(
                f"Missing OAuth client file: {GOOGLE_CLIENT_SECRET_FILE}. Download it from Google Cloud and place it there."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CLIENT_SECRET_FILE), SCOPES)
        credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=credentials)
