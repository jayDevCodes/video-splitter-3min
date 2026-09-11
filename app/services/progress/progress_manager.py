from __future__ import annotations

from typing import Any

from app.services.jobs.job_manager import job_manager


def emit(job_id: str, event: str, **data: Any) -> dict[str, Any]:
    return job_manager.emit(job_id, event, data)


def start_task(job_id: str, task: str, *, label: str, **data: Any) -> dict[str, Any]:
    return emit(job_id, "task_started", task=task, label=label, status="running", progress=0, **data)


def progress(job_id: str, task: str, value: int | float, *, label: str | None = None, **data: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"task": task, "status": "running", "progress": max(0, min(100, value)), **data}
    if label is not None:
        payload["label"] = label
    return emit(job_id, "task_progress", **payload)


def complete_task(job_id: str, task: str, *, label: str | None = None, **data: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"task": task, "status": "completed", "progress": 100, **data}
    if label is not None:
        payload["label"] = label
    return emit(job_id, "task_completed", **payload)


def fail_task(job_id: str, task: str, error: str, *, label: str | None = None, **data: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"task": task, "status": "failed", "progress": 100, "error": error, **data}
    if label is not None:
        payload["label"] = label
    return emit(job_id, "task_failed", **payload)
