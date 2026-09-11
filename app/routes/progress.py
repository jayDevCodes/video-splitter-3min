from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.jobs.job_manager import TERMINAL_STATUSES, job_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def job_status(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _sse(event: dict) -> str:
    return (
        f"id: {event['sequence']}\n"
        f"event: {event['event']}\n"
        f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


@router.get("/{job_id}/events")
async def job_events(job_id: str, since: int = Query(0, ge=0)):
    if not job_manager.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    async def stream():
        cursor = since
        idle_cycles = 0
        while True:
            events = job_manager.events_since(job_id, cursor)
            if events:
                idle_cycles = 0
                for event in events:
                    cursor = event["sequence"]
                    yield _sse(event)
                current = job_manager.get(job_id)
                if current and current["status"] in TERMINAL_STATUSES:
                    return
            else:
                idle_cycles += 1
                current = job_manager.get(job_id)
                if current and current["status"] in TERMINAL_STATUSES:
                    return
                if idle_cycles % 8 == 0:
                    yield ": keep-alive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
