from __future__ import annotations

import html
import json
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse

from app.services.oauth.meta_facebook import (
    complete_flow,
    get_flow,
    handle_callback,
    start_flow,
)
from app.services.oauth.upload_post_facebook import (
    complete_flow as managed_complete_flow,
    finish_flow as managed_finish_flow,
    get_flow as managed_get_flow,
    start_flow as managed_start_flow,
)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


class FacebookCompletePayload(BaseModel):
    flow_id: str = Field(min_length=16)
    page_ids: list[str] = Field(min_length=1)


def _callback_message(message: dict, status_code: int = 200) -> HTMLResponse:
    payload = json.dumps(message)
    body = (
        "<!doctype html><html><body><script>"
        f"window.opener?.postMessage({payload}, window.location.origin); window.close();"
        "</script><p>Connection complete. You can close this window.</p></body></html>"
    )
    return HTMLResponse(body, status_code=status_code)


@router.get("/facebook/managed/start")
def facebook_managed_start(request: Request):
    callback_url = str(request.url_for("facebook_managed_callback"))
    try:
        return managed_start_flow(callback_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/facebook/managed/callback", response_class=HTMLResponse, name="facebook_managed_callback")
def facebook_managed_callback(
    state: str | None = None,
    connect_status: str | None = None,
    error_code: str | None = None,
):
    if not state:
        return _callback_message(
            {"type": "managed-facebook-oauth", "status": "error", "message": "Missing connection state."},
            400,
        )
    try:
        result = managed_finish_flow(state, connect_status or "error", error_code)
        message = {
            "type": "managed-facebook-oauth",
            "status": "ready",
            "flow_id": result["flow_id"],
            "page_count": len(result.get("pages", [])),
        }
        return _callback_message(message)
    except (ValueError, RuntimeError) as exc:
        return _callback_message(
            {"type": "managed-facebook-oauth", "status": "error", "message": html.escape(str(exc))},
            400,
        )


@router.get("/facebook/managed/pages")
def facebook_managed_pages(flow_id: str):
    flow = managed_get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Facebook connection expired. Start again.")
    try:
        result = managed_finish_flow(flow_id, "success")
        return {
            "flow_id": flow_id,
            "pages": result.get("pages", []),
        }
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/facebook/managed/complete")
def facebook_managed_complete(payload: FacebookCompletePayload):
    try:
        accounts = managed_complete_flow(payload.flow_id, payload.page_ids)
        return {"accounts": accounts}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
