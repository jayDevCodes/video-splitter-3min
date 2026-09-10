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
        "output_directory": str(output_dir.relative_to(output_dir.parent.parent)),
        "generated_now": len(generated),
        "uploaded": uploaded_count,
        "remaining": len(pending),
        "failed": failed_count,
        "state": state,
        "ready": (output_dir / "READY").exists(),
        "pending_order": [path.name for path in pending],
    }
