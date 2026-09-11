from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR
from app.services.file_manager import cleanup_file, make_output_directory
from app.services.jobs.job_manager import job_manager
from app.services.metadata_manager import mark_ready
from app.services.progress import progress_manager
from app.services.video_analyzer import probe_video
from app.services.video_splitter import split_video


def run_split_job(
    job_id: str,
    input_path: Path,
    original_filename: str,
    chunk_seconds: int,
    orientation: str,
) -> None:
    try:
        job_manager.update(job_id, status="running", event="job_started", task="video_split", progress=0)
        output_dir = make_output_directory(original_filename)

        progress_manager.emit(job_id, "task_started", task="video_analyze", label="Analyzing video", status="running", progress=5)
        info = probe_video(input_path)
        progress_manager.emit(job_id, "task_completed", task="video_analyze", label="Video analyzed", status="completed", progress=10, duration=info.duration)

        def on_progress(event: str, index: int, total: int) -> None:
            base = 10
            span = 85
            value = base + int((index - (1 if event == "part_started" else 0)) / max(total, 1) * span)
            progress_manager.emit(
                job_id,
                "split_progress",
                task="video_split",
                label="Creating Shorts",
                status="running" if event == "part_started" else "encoding",
                progress=max(10, min(95, value)),
                part=index,
                total_parts=total,
                part_status=event,
            )

        parts = split_video(input_path, output_dir, info, chunk_seconds, orientation, progress_callback=on_progress)
        mark_ready(output_dir)
        result: dict[str, Any] = {
            "source_filename": original_filename,
            "output_directory": str(output_dir.relative_to(OUTPUT_DIR.parent)),
            "total_duration": info.duration,
            "chunk_seconds": chunk_seconds,
            "parts_created": len(parts),
            "parts": [p.name for p in parts],
        }
        progress_manager.emit(job_id, "task_completed", task="video_split", label="Shorts generated", status="completed", progress=100, result=result)
        job_manager.update(job_id, status="completed", event="job_completed", task="video_split", progress=100, result=result)
    except Exception as exc:
        progress_manager.emit(job_id, "task_failed", task="video_split", label="Video split failed", status="failed", progress=100, error=str(exc))
        job_manager.update(job_id, status="failed", event="job_failed", task="video_split", progress=100, error=str(exc))
    finally:
        cleanup_file(input_path)
