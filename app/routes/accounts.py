from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.account_manager import delete_account, get_accounts_by_platform, upsert_account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountPayload(BaseModel):
    id: str
    platform: str
    name: str
    type: str = "account"
    enabled: bool = True
    configured: bool = False
    external_id: str | None = None


@router.get("")
def accounts():
    return {"accounts": get_accounts_by_platform()}


@router.post("")
def add_account(payload: AccountPayload):
    try:
        return {"account": upsert_account(payload.model_dump())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{account_id}")
def remove_account(account_id: str):
    delete_account(account_id)
    return {"deleted": account_id}
