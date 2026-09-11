from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
FRONTEND_DIR = BASE_DIR / "frontend"
CREDENTIALS_DIR = BASE_DIR / "credentials"
TOKENS_DIR = BASE_DIR / "tokens"
GOOGLE_CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
GOOGLE_TOKEN_FILE = TOKENS_DIR / "token.json"

DEFAULT_CHUNK_SECONDS = int(os.getenv("CHUNK_SECONDS", "180"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5120"))
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", "ffprobe")
UPLOAD_WATCH_INTERVAL = int(os.getenv("UPLOAD_WATCH_INTERVAL", "15"))

# Meta / Facebook OAuth configuration. Keep the app secret server-side only.
META_APP_ID = os.getenv("META_APP_ID", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v26.0").strip()
META_OAUTH_REDIRECT_URI = os.getenv(
    "META_OAUTH_REDIRECT_URI",
    "http://localhost:8000/api/oauth/facebook/callback",
).strip()
META_OAUTH_SCOPES = [
    "public_profile",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
]

for directory in (INPUT_DIR, OUTPUT_DIR, TEMP_DIR, CREDENTIALS_DIR, TOKENS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
