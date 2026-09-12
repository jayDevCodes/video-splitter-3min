from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

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

# Direct Meta integration remains available for development, but is optional.
META_APP_ID = os.getenv("META_APP_ID", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v26.0").strip()
META_OAUTH_CONFIG_ID = os.getenv("META_OAUTH_CONFIG_ID", "").strip()
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

# Managed social provider. This is the user-facing, no-Meta-credentials path.
UPLOAD_POST_API_BASE = os.getenv("UPLOAD_POST_API_BASE", "https://api.upload-post.com").strip()
UPLOAD_POST_API_KEY = os.getenv("UPLOAD_POST_API_KEY", "").strip()
UPLOAD_POST_PROFILE = os.getenv("UPLOAD_POST_PROFILE", "video_splitter_local").strip()

for directory in (INPUT_DIR, OUTPUT_DIR, TEMP_DIR, CREDENTIALS_DIR, TOKENS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def missing_meta_oauth_config() -> list[str]:
    missing = []
    if not META_APP_ID:
        missing.append("META_APP_ID")
    if not META_APP_SECRET:
        missing.append("META_APP_SECRET")
    if not META_OAUTH_REDIRECT_URI:
        missing.append("META_OAUTH_REDIRECT_URI")
    return missing


def managed_facebook_configured() -> bool:
    return bool(UPLOAD_POST_API_KEY and UPLOAD_POST_PROFILE)
