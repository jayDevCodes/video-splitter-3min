from __future__ import annotations

import html
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse

from app.services.oauth.meta_facebook import (
    complete_flow,
    get_flow,
    handle_callback,
    start_flow,
)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


class FacebookCompletePayload(BaseModel):
    flow_id: str = Field(min_length=16)
    page_ids: list[str] = Field(min_length=1)


@router.get("/facebook/start")
def facebook_start():
    try:
        return start_flow()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/facebook/callback", response_class=HTMLResponse)
def facebook_callback(code: str | None = None, state: str | None = None, error: str | None = None, error_description: str | None = None):
    safe_error = html.escape(error_description or error or "Facebook authorization failed.")
    if error or not code or not state:
        payload = json.dumps({"type": "meta-oauth", "status": "error", "message": safe_error})
        return HTMLResponse(
            f"""<!doctype html><html><body><script>window.opener?.postMessage({payload}, window.location.origin); window.close();</script><p>{safe_error}</p></body></html>""",
            status_code=400,
        )

    try:
        flow = handle_callback(code, state)
        message = {"type": "meta-oauth", "status": "ready", "flow_id": flow.state, "page_count": len(flow.pages or [])}
        payload = json.dumps(message)
        return HTMLResponse(
            f"""<!doctype html><html><body><script>window.opener?.postMessage({payload}, window.location.origin); window.close();</script><p>Facebook connected. You can close this window.</p></body></html>"""
        )
    except (ValueError, RuntimeError) as exc:
        message = {"type": "meta-oauth", "status": "error", "message": str(exc)}
        payload = json.dumps(message)
        return HTMLResponse(
            f"""<!doctype html><html><body><script>window.opener?.postMessage({payload}, window.location.origin); window.close();</script><p>{html.escape(str(exc))}</p></body></html>""",
            status_code=400,
        )


@router.get("/facebook/pages")
def facebook_pages(flow_id: str):
    flow = get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Facebook connection expired. Start again.")
    return {
        "flow_id": flow_id,
        "pages": [{"id": page["id"], "name": page["name"]} for page in (flow.pages or [])],
    }


@router.post("/facebook/complete")
def facebook_complete(payload: FacebookCompletePayload):
    try:
        accounts = complete_flow(payload.flow_id, payload.page_ids)
        return {"accounts": accounts}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

