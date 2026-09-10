from __future__ import annotations

from pathlib import Path

from app.services.metadata_manager import load_status
from app.services.youtube_uploader import VIDEO_RE, _part_number


def _pending_parts(output_dir: Path) -> list[Path]:
    status = load_status(output_dir)
    uploaded = {
        name
        for name, item in status.get("files", {}).items()
        if item.get("status") == "uploaded"
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
    uploaded_count = sum(
        1 for item in files_status.values() if item.get("status") == "uploaded"
    )
    pending = _pending_parts(output_dir)
    failed_count = sum(
        1 for item in files_status.values() if item.get("status") == "failed"
    )

    if pending:
        state = "partial" if uploaded_count else "not_started"
    elif generated or uploaded_count:
        state = "complete"
    else:
        state = "empty"

    return {
        "folder": output_dir.name,
        "output_directory": str(output_dir.relative_to(output_dir.parents[len(output_dir.parts) - len(output_dir.parents[0].parts) - 1])) if False else str(output_dir.relative_to(Path.cwd() if OUTPUT_ROOT := None else output_dir.parent)),
        "generated_now": len(generated),
        "uploaded": uploaded_count,
        "remaining": len(pending),
        "failed": failed_count,
        "state": state,
        "ready": (output_dir / "READY").exists(),
        "pending_order": [path.name for path in pending],
    }


def discover_upload_folders(output_root: Path) -> list[dict]:
    """Find any directory under output_root that contains unuploaded video parts.

    This supports both the current layout (output/<video>/part_*.mp4) and
    older/nested layouts (output/<video>/<subfolder>/part_*.mp4).
    """
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
