from __future__ import annotations

import secrets
from dataclasses import dataclass
from time import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import UPLOAD_POST_API_BASE, UPLOAD_POST_API_KEY, UPLOAD_POST_PROFILE

FLOW_TTL_SECONDS = 15 * 60


@dataclass
class ManagedFacebookFlow:
    state: str
    profile_username: str
    created_at: float


_flows: dict[str, ManagedFacebookFlow] = {}


def _headers() -> dict[str, str]:
    if not UPLOAD_POST_API_KEY:
        raise RuntimeError("Managed Facebook connection is not configured. Set UPLOAD_POST_API_KEY in .env.")
    return {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}", "Accept": "application/json"}


def _cleanup() -> None:
    cutoff = time() - FLOW_TTL_SECONDS
    for state, flow in list(_flows.items()):
        if flow.created_at < cutoff:
            _flows.pop(state, None)


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{UPLOAD_POST_API_BASE.rstrip('/')}{path}"
    try:
        response = httpx.request(method, url, headers=_headers(), timeout=30, **kwargs)
        payload = response.json() if response.content else {}
    except Exception as exc:
        raise RuntimeError(f"Managed social provider request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = payload.get("message") or payload.get("error") or response.text[:300]
        raise RuntimeError(str(detail))
    return payload if isinstance(payload, dict) else {}


def _ensure_profile() -> None:
    try:
        _request(
            "POST",
            "/api/uploadposts/users",
            json={"username": UPLOAD_POST_PROFILE},
        )
    except RuntimeError as exc:
        # Upload-Post returns an error if the stable profile already exists.
        # Verify it is usable instead of treating that as a fatal condition.
        existing = _request("GET", "/api/uploadposts/users")
        profiles = existing.get("users") or existing.get("profiles") or existing.get("data") or []
        if not any(str(item.get("username")) == UPLOAD_POST_PROFILE for item in profiles if isinstance(item, dict)):
            raise exc


def start_flow(callback_url: str) -> dict[str, str]:
    if not UPLOAD_POST_API_KEY:
        raise RuntimeError("Managed Facebook connection is not configured. Set UPLOAD_POST_API_KEY in .env.")

    _cleanup()
    _ensure_profile()
    state = secrets.token_urlsafe(32)
    _flows[state] = ManagedFacebookFlow(
        state=state,
        profile_username=UPLOAD_POST_PROFILE,
        created_at=time(),
    )

    result = _request(
        "POST",
        "/api/uploadposts/users/generate-jwt",
        json={
            "username": UPLOAD_POST_PROFILE,
            "redirect_url": callback_url,
            "platforms": ["facebook"],
            "connect_title": "Connect Facebook Page",
            "connect_description": "Securely connect your Facebook Pages for video publishing.",
            "redirect_button_text": "Return to Video Splitter",
            "show_calendar": False,
        },
    )
    access_url = str(result.get("access_url") or "")
    if not access_url:
        raise RuntimeError("Managed provider did not return a connection URL.")

    return {"flow_id": state, "login_url": access_url, "mode": "managed_provider"}


def get_flow(state: str) -> ManagedFacebookFlow | None:
    _cleanup()
    return _flows.get(state)


def finish_flow(state: str, connect_status: str, error_code: str | None = None) -> dict[str, Any]:
    _cleanup()
    flow = _flows.get(state)
    if not flow:
        raise ValueError("Facebook connection expired. Start again.")
    if connect_status != "success":
        _flows.pop(state, None)
        message = error_code or "Facebook connection was cancelled or failed."
        raise ValueError(message)

    pages = _request(
        "GET",
        "/api/uploadposts/facebook/pages",
        params={"profile": flow.profile_username},
    ).get("pages", [])
    clean_pages = []
    for page in pages:
        if not isinstance(page, dict) or not page.get("page_id") or not page.get("page_name"):
            continue
        clean_pages.append(
            {
                "id": str(page["page_id"]),
                "name": str(page["page_name"]),
                "picture": page.get("picture"),
            }
        )
    return {"flow_id": state, "profile_username": flow.profile_username, "pages": clean_pages}


def complete_flow(state: str, page_ids: list[str]) -> list[dict[str, Any]]:
    from app.services.account_manager import upsert_account

    flow = get_flow(state)
    if not flow:
        raise ValueError("Facebook connection expired. Connect again.")

    pages = finish_flow(state, "success")["pages"]
    requested = {str(value).strip() for value in page_ids if str(value).strip()}
    selected = [page for page in pages if page["id"] in requested]
    if not selected:
        raise ValueError("Select at least one Facebook Page.")

    created = []
    for page in selected:
        account = upsert_account(
            {
                "id": f"fb_{page['id']}",
                "platform": "facebook",
                "type": "page",
                "name": page["name"],
                "external_id": page["id"],
                "enabled": True,
                "configured": True,
                "auth_provider": "upload_post",
                "provider_profile": flow.profile_username,
                "provider_page_id": page["id"],
                "provider_page_name": page["name"],
            }
        )
        created.append({k: v for k, v in account.items() if k not in {"token_file", "credential_ref"}})

    _flows.pop(state, None)
    return created
