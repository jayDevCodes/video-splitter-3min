from __future__ import annotations

from pathlib import Path

from app.config import OUTPUT_DIR
from app.services.metadata_manager import load_status
from app.services.youtube_uploader import VIDEO_RE, _part_number


def _is_uploaded_for_platform(item: dict, platform: str) -> bool:
    if item.get("status") == "uploaded":
        return True
    return item.get("platforms", {}).get(platform, {}).get("status") == "uploaded"


def _pending_parts(output_dir: Path, platform: str = "youtube") -> list[Path]:
    status = load_status(output_dir)
    uploaded = {
        name
        for name, item in status.get("files", {}).items()
        if _is_uploaded_for_platform(item, platform)
    }
    return [
        path
        for path in sorted(output_dir.glob("part_*.mp4"), key=_part_number)
        if path.name not in uploaded
    ]


def folder_summary(output_dir: Path) -> dict:
    status = load_status(output_dir)
    files_status = status.get("files", {})
    generated = sorted(output_dir.glob("part_*.mp4"), key=_part_number)
    uploaded_count = sum(1 for item in files_status.values() if _is_uploaded_for_platform(item, "youtube"))
    pending = _pending_parts(output_dir, "youtube")
    failed_count = sum(
        1 for item in files_status.values()
        if item.get("status") == "failed" or item.get("platforms", {}).get("youtube", {}).get("status") == "failed"
    )

    if pending:
        state = "partial" if uploaded_count else "not_started"
    elif generated or uploaded_count:
        state = "complete"
    else:
        state = "empty"

    return {
        "folder": output_dir.name,
        "output_directory": str(output_dir.relative_to(OUTPUT_DIR.parent)),
        "generated_now": len(generated),
        "uploaded": uploaded_count,
        "remaining": len(pending),
        "failed": failed_count,
        "state": state,
        "ready": (output_dir / "READY").exists(),
        "pending_order": [path.name for path in pending],
    }


def discover_upload_folders(output_root: Path) -> list[dict]:
    """Find output directories with pending Shorts, preserving old/new status formats."""
    if not output_root.exists():
        return []

    folders: list[dict] = []
    seen: set[Path] = set()
    for part in output_root.rglob("part_*.mp4"):
        output_dir = part.parent
        if output_dir in seen:
            continue
        seen.add(output_dir)
        summary = folder_summary(output_dir)
        if summary["remaining"] > 0:
            folders.append(summary)

    return sorted(folders, key=lambda item: item["output_directory"].lower())
