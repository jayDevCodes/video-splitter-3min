from app.services import account_manager


def test_upsert_and_resolve_accounts(tmp_path, monkeypatch):
    accounts_file = tmp_path / "accounts.json"
    accounts_dir = tmp_path
    monkeypatch.setattr(account_manager, "ACCOUNTS_DIR", accounts_dir)
    monkeypatch.setattr(account_manager, "ACCOUNTS_FILE", accounts_file)

    account_manager.upsert_account({
        "id": "yt_001",
        "platform": "youtube",
        "name": "Channel One",
        "configured": True,
    })
    account_manager.upsert_account({
        "id": "fb_001",
        "platform": "facebook",
        "name": "Page One",
        "configured": False,
    })

    grouped = account_manager.get_accounts_by_platform()
    assert grouped["youtube"][0]["id"] == "yt_001"
    assert grouped["facebook"][0]["id"] == "fb_001"
    assert "token_file" not in grouped["youtube"][0]

    resolved = account_manager.resolve_targets([{"account_id": "yt_001", "platform": "youtube"}])
    assert resolved[0]["id"] == "yt_001"


def test_disabled_account_cannot_be_target(tmp_path, monkeypatch):
    accounts_file = tmp_path / "accounts.json"
    monkeypatch.setattr(account_manager, "ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr(account_manager, "ACCOUNTS_FILE", accounts_file)
    account_manager.upsert_account({
        "id": "ig_001",
        "platform": "instagram",
        "name": "IG One",
        "enabled": False,
        "configured": True,
    })

    try:
        account_manager.resolve_targets([{"account_id": "ig_001", "platform": "instagram"}])
    except ValueError as exc:
        assert "Unknown or disabled" in str(exc)
    else:
        raise AssertionError("Disabled account should not resolve")
