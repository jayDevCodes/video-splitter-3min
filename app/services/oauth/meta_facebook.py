from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import (
    META_APP_ID,
    META_APP_SECRET,
    META_GRAPH_API_VERSION,
    META_OAUTH_REDIRECT_URI,
    META_OAUTH_SCOPES,
    TOKENS_DIR,
)

FLOW_TTL_SECONDS = 10 * 60
_GRAPH_BASE = "https://graph.facebook.com"
_DIALOG_BASE = "https://www.facebook.com"
_ID_RE = re.compile(r"[^a-zA-Z0-9_-]+")

# Compatibility/test-isolation alias. Account records are persisted by account_manager.
ACCOUNTS_DIR = TOKENS_DIR


@dataclass
class FacebookOAuthFlow:
    state: str
    created_at: float
    user_access_token: str | None = None
    pages: list[dict[str, Any]] | None = None
    completed: bool = False


_flows: dict[str, FacebookOAuthFlow] = {}
_lock = Lock()


def _require_config() -> None:
    missing = []
    if not META_APP_ID:
        missing.append("META_APP_ID")
    if not META_APP_SECRET:
        missing.append("META_APP_SECRET")
    if not META_OAUTH_REDIRECT_URI:
        missing.append("META_OAUTH_REDIRECT_URI")
    if missing:
        raise RuntimeError("Missing Meta OAuth configuration: " + ", ".join(missing))


def _cleanup_flows() -> None:
    cutoff = time() - FLOW_TTL_SECONDS
    stale = [key for key, flow in _flows.items() if flow.created_at < cutoff]
    for key in stale:
        _flows.pop(key, None)


def _graph_request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{_GRAPH_BASE}/{META_GRAPH_API_VERSION}/{path.lstrip('/')}"
    query = urlencode({key: value for key, value in params.items() if value is not None})
    request = Request(f"{url}?{query}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Meta Graph API request failed: {exc}") from exc
    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message", "Meta Graph API returned an error.") if isinstance(error, dict) else str(error)
        raise RuntimeError(message)
    return payload if isinstance(payload, dict) else {}


def start_flow() -> dict[str, str]:
    _require_config()
    with _lock:
        _cleanup_flows()
        state = secrets.token_urlsafe(32)
        _flows[state] = FacebookOAuthFlow(state=state, created_at=time())

    params = {
        "client_id": META_APP_ID,
        "redirect_uri": META_OAUTH_REDIRECT_URI,
        "state": state,
        "scope": ",".join(META_OAUTH_SCOPES),
        "response_type": "code",
    }
    return {
        "flow_id": state,
        "login_url": f"{_DIALOG_BASE}/{META_GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}",
    }


def handle_callback(code: str, state: str) -> FacebookOAuthFlow:
    _require_config()
    with _lock:
        _cleanup_flows()
        flow = _flows.get(state)
    if not flow:
        raise ValueError("OAuth state expired or is invalid. Start Facebook connection again.")

    token_response = _graph_request(
        "/oauth/access_token",
        {
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "redirect_uri": META_OAUTH_REDIRECT_URI,
            "code": code,
        },
    )
    user_token = str(token_response.get("access_token", ""))
    if not user_token:
        raise RuntimeError("Meta did not return a user access token.")

    pages_response = _graph_request(
        "/me/accounts",
        {
            "access_token": user_token,
            "fields": "id,name,access_token",
            "limit": 200,
        },
    )
    pages = []
    for page in pages_response.get("data", []):
        if not isinstance(page, dict) or not page.get("id") or not page.get("name"):
            continue
        # The Page access token never leaves the backend.
        pages.append(
            {
                "id": str(page["id"]),
                "name": str(page["name"]),
                "access_token": str(page.get("access_token", "")),
            }
        )

    with _lock:
        flow.user_access_token = user_token
        flow.pages = pages
    return flow


def get_flow(state: str) -> FacebookOAuthFlow | None:
    with _lock:
        _cleanup_flows()
        return _flows.get(state)


def complete_flow(state: str, page_ids: list[str]) -> list[dict[str, Any]]:
    from app.services.account_manager import upsert_account

    with _lock:
        _cleanup_flows()
        flow = _flows.get(state)
        if not flow:
            raise ValueError("OAuth flow expired. Connect Facebook again.")
        pages = list(flow.pages or [])

    requested = {str(value).strip() for value in page_ids if str(value).strip()}
    selected = [page for page in pages if page["id"] in requested]
    if not selected:
        raise ValueError("Select at least one Facebook Page.")

    created = []
    for page in selected:
        page_token = page.get("access_token")
        if not page_token:
            raise ValueError(f"No Page access token was returned for {page['name']}.")

        account_id = f"fb_{page['id']}"
        safe_id = _ID_RE.sub("_", account_id)
        credential_file = TOKENS_DIR / f"meta_{safe_id}.json"
        credential_file.parent.mkdir(parents=True, exist_ok=True)
        credential_file.write_text(
            json.dumps(
                {
                    "platform": "facebook",
                    "page_id": page["id"],
                    "page_name": page["name"],
                    "page_access_token": page_token,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            os.chmod(credential_file, 0o600)
        except OSError:
            pass

        account = upsert_account(
            {
                "id": account_id,
                "platform": "facebook",
                "type": "page",
                "name": page["name"],
                "external_id": page["id"],
                "enabled": True,
                "configured": True,
                "credential_ref": str(credential_file.relative_to(TOKENS_DIR)),
                "auth_provider": "meta",
            }
        )
        public = {key: value for key, value in account.items() if key not in {"token_file", "credential_ref"}}
        created.append(public)

    with _lock:
        if state in _flows:
            _flows[state].completed = True
            _flows.pop(state, None)
    return created


def clear_flow(state: str) -> None:
    with _lock:
        _flows.pop(state, None)
