from pathlib import Path
import re
import shutil
import uuid
from app.config import INPUT_DIR, OUTPUT_DIR

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts"}


def safe_stem(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return cleaned[:80] or "video"


def save_upload(upload_file, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported video format: {suffix or 'unknown'}")
    destination = INPUT_DIR / f"{uuid.uuid4().hex}{suffix}"
    with destination.open("wb") as output:
        shutil.copyfileobj(upload_file.file, output, length=1024 * 1024)
    return destination


def make_output_directory(filename: str) -> Path:
    directory = OUTPUT_DIR / f"{safe_stem(filename)}_{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def cleanup_file(path: Path) -> None:
    path.unlink(missing_ok=True)
