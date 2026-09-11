from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.jobs.job_manager import job_manager
from app.services.multi_platform_uploader import run_multi_platform_upload


def run_upload_job(
    job_id: str,
    output_dir: Path,
    *,
    targets: list[dict[str, str]],
    metadata: dict[str, Any],
    gap_seconds: int,
    delete_after_upload: bool,
    job_path: Path,
) -> None:
    job_manager.update(job_id, status="running", event="job_started", task="upload", progress=0)
    try:
        result = run_multi_platform_upload(
            output_dir,
            targets=targets,
            metadata=metadata,
            gap_seconds=gap_seconds,
            delete_after_upload=delete_after_upload,
            job_id=job_id,
        )
        status = "failed" if result.get("stopped_on_error") else "completed"
        job_manager.update(
            job_id,
            status=status,
            event="job_completed" if status == "completed" else "job_failed",
            task="upload",
            progress=100,
            result=result,
        )
        if job_path:
            existing = {}
            if job_path.exists():
                try:
                    existing = json.loads(job_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    existing = {}
            existing.update({"status": status, "job_id": job_id})
            job_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        job_manager.update(job_id, status="failed", event="job_failed", task="upload", error=str(exc), progress=100)
        if job_path:
            existing = {}
            if job_path.exists():
                try:
                    existing = json.loads(job_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    existing = {}
            existing.update({"status": "failed", "job_id": job_id, "error": str(exc)})
            job_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
