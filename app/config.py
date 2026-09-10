from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
FRONTEND_DIR = BASE_DIR / "frontend"

DEFAULT_CHUNK_SECONDS = int(os.getenv("CHUNK_SECONDS", "180"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5120"))
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", "ffprobe")

for directory in (INPUT_DIR, OUTPUT_DIR, TEMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)
