from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR_NAME = "_config"
METADATA_FILE = "metadata.json"
STATUS_FILE = "upload_status.json"
READY_FILE = "READY"


def config_dir(output_dir: Path) -> Path:
    path = output_dir / CONFIG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_metadata(
    output_dir: Path,
    *,
    title_template: str,
    description: str,
    tags: list[str],
    thumbnail: str | None,
    privacy: str,
    category_id: str,
    made_for_kids: bool,
    auto_upload: bool,
    gap_seconds: int | None = None,
    delete_after_upload: bool = True,
) -> Path:
    if privacy not in {"private", "unlisted", "public"}:
        raise ValueError("privacy must be private, unlisted, or public")
    metadata = {
        "title_template": title_template.strip() or "{filename} #{number}",
        "description": description,
        "tags": tags,
        "thumbnail": thumbnail,
        "youtube": {"privacy": privacy, "category_id": category_id, "made_for_kids": made_for_kids},
        "upload": {
            "enabled": True,
            "auto_upload": auto_upload,
            "gap_seconds": 60 if gap_seconds is None else gap_seconds,
            "delete_after_upload": delete_after_upload,
        },
    }
    path = config_dir(output_dir) / METADATA_FILE
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_metadata(output_dir: Path) -> dict:
    path = output_dir / CONFIG_DIR_NAME / METADATA_FILE
    if not path.exists():
        raise FileNotFoundError(f"Missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_status(output_dir: Path) -> dict:
    path = output_dir / CONFIG_DIR_NAME / STATUS_FILE
    if not path.exists():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_status(output_dir: Path, status: dict) -> None:
    path = config_dir(output_dir) / STATUS_FILE
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")


def mark_ready(output_dir: Path) -> None:
    (output_dir / READY_FILE).touch()


def is_ready(output_dir: Path) -> bool:
    return (output_dir / READY_FILE).exists()


def render_title(template: str, *, number: int, filename: str) -> str:
    values = {"number": number, "filename": filename}
    try:
        return template.format(**values).strip()
    except (KeyError, ValueError):
        return f"{filename} #{number}"
