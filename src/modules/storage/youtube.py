"""YouTube Upload Automation - OAuth-based, no paid APIs."""
import json
import os
from pathlib import Path
from typing import Optional


class YouTubeUploader:
    """Uploads videos to YouTube using OAuth2 (free, official API).

    Setup:
    1. Go to Google Cloud Console (free tier)
    2. Enable YouTube Data API v3
    3. Create OAuth2 credentials (Desktop app)
    4. Download client_secrets.json to config/
    5. First run will open browser for auth
    """

    def __init__(self, secrets_path: str = "config/client_secrets.json"):
        self.secrets_path = secrets_path
        self.token_path = "config/youtube_token.json"

    def upload(self, video_path: str, title: str, description: str,
               tags: list = None, category: str = "24", privacy: str = "public") -> Optional[str]:
        """Upload video and return video ID."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            raise RuntimeError(
                "Install: pip install google-api-python-client google-auth-oauthlib"
            )

        creds = self._get_credentials()
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or ["ai", "cartoon", "story"],
                "categoryId": category,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()

        return response.get("id")

    def _get_credentials(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
            Path(self.token_path).write_text(creds.to_json())

        return creds
