from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class JobManager:
    def __init__(self, max_events: int = 2000) -> None:
        self._lock = Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._max_events = max_events

    def create(self, kind: str, payload: dict[str, Any] | None = None) -> str:
        job_id = f"JOB-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "kind": kind,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "payload": deepcopy(payload or {}),
                "events": [],
                "next_event_id": 1,
            }
        self.emit(job_id, "job_queued", {"status": "queued", "task": kind})
        return job_id

    def emit(self, job_id: str, event: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(f"Unknown job: {job_id}")
            event_data = {
                "job_id": job_id,
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(data or {}),
            }
            seq = job["next_event_id"]
            job["next_event_id"] += 1
            event_data["sequence"] = seq
            job["events"].append(event_data)
            if len(job["events"]) > self._max_events:
                del job["events"][:-self._max_events]
            job["updated_at"] = event_data["timestamp"]
            if "status" in event_data:
                job["status"] = event_data["status"]
            if "result" in event_data:
                job["result"] = deepcopy(event_data["result"])
            if "error" in event_data:
                job["error"] = event_data["error"]
            return deepcopy(event_data)

    def update(self, job_id: str, status: str | None = None, **data: Any) -> dict[str, Any]:
        if status is not None:
            data["status"] = status
        return self.emit(job_id, data.pop("event", "job_update"), data)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return deepcopy(job) if job else None

    def events_since(self, job_id: str, sequence: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(f"Unknown job: {job_id}")
            return [deepcopy(item) for item in job["events"] if item["sequence"] > sequence]


job_manager = JobManager()
