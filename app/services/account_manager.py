from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ACCOUNTS_DIR = BASE_DIR / "tokens"
ACCOUNTS_FILE = ACCOUNTS_DIR / "accounts.json"
LEGACY_YOUTUBE_ID = "yt_default"


def _ensure_file() -> None:
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    if not ACCOUNTS_FILE.exists():
        ACCOUNTS_FILE.write_text(json.dumps({"accounts": []}, indent=2), encoding="utf-8")


def ensure_legacy_youtube_account() -> dict[str, Any] | None:
    """Bootstrap the old single YouTube token account only at app startup."""
    _ensure_file()
    accounts = list_accounts()
    for account in accounts:
        if account.get("id") == LEGACY_YOUTUBE_ID:
            return account
    token_file = ACCOUNTS_DIR / "token.json"
    if not token_file.exists():
        return None
    account = {
        "id": LEGACY_YOUTUBE_ID,
        "platform": "youtube",
        "type": "channel",
        "name": "YouTube (connected account)",
        "enabled": True,
        "configured": True,
        "token_file": str(token_file),
        "legacy": True,
    }
    accounts.append(account)
    save_accounts(accounts)
    return account


def list_accounts() -> list[dict[str, Any]]:
    _ensure_file()
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        accounts = data.get("accounts", [])
        return accounts if isinstance(accounts, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_accounts(accounts: list[dict[str, Any]]) -> None:
    _ensure_file()
    ACCOUNTS_FILE.write_text(json.dumps({"accounts": accounts}, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_account(account: dict[str, Any]) -> dict[str, Any]:
    required = {"id", "platform", "name"}
    missing = required - set(account)
    if missing:
        raise ValueError(f"Missing account fields: {', '.join(sorted(missing))}")
    platform = str(account["platform"]).lower().strip()
    if platform not in {"youtube", "facebook", "instagram"}:
        raise ValueError(f"Unsupported platform: {platform}")
    normalized = {**account, "platform": platform, "enabled": bool(account.get("enabled", True))}
    if platform == "youtube":
        normalized["token_file"] = str(account.get("token_file") or (ACCOUNTS_DIR / f"youtube_{account['id']}.json"))
    accounts = [a for a in list_accounts() if a.get("id") != normalized["id"]]
    accounts.append(normalized)
    save_accounts(accounts)
    return normalized


def delete_account(account_id: str) -> None:
    save_accounts([a for a in list_accounts() if a.get("id") != account_id])


def get_accounts_by_platform() -> dict[str, list[dict[str, Any]]]:
    result = {"youtube": [], "facebook": [], "instagram": []}
    for account in list_accounts():
        platform = account.get("platform")
        if platform in result and account.get("enabled", True):
            public = {
                k: v
                for k, v in account.items()
                if k not in {"token_file", "credential_ref"}
            }
            result[platform].append(public)
    return result


def resolve_targets(targets: list[dict[str, str]]) -> list[dict[str, Any]]:
    accounts = {a.get("id"): a for a in list_accounts() if a.get("enabled", True)}
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for target in targets:
        account_id = str(target.get("account_id", "")).strip()
        if not account_id or account_id in seen:
            continue
        account = accounts.get(account_id)
        if not account:
            raise ValueError(f"Unknown or disabled account: {account_id}")
        seen.add(account_id)
        resolved.append(account)
    if not resolved:
        raise ValueError("Select at least one account target.")
    return resolved
