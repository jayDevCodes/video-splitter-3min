from pathlib import Path

from app.services.oauth import meta_facebook


def test_start_flow_requires_meta_configuration(monkeypatch):
    monkeypatch.setattr(meta_facebook, "META_APP_ID", "")
    monkeypatch.setattr(meta_facebook, "META_APP_SECRET", "")
    try:
        meta_facebook.start_flow()
    except RuntimeError as exc:
        assert "META_APP_ID" in str(exc)
        assert "META_APP_SECRET" in str(exc)
    else:
        raise AssertionError("Missing Meta configuration should fail")


def test_start_flow_builds_oauth_url(monkeypatch):
    monkeypatch.setattr(meta_facebook, "META_APP_ID", "123")
    monkeypatch.setattr(meta_facebook, "META_APP_SECRET", "secret")
    monkeypatch.setattr(meta_facebook, "META_OAUTH_REDIRECT_URI", "http://localhost:8000/api/oauth/facebook/callback")
    monkeypatch.setattr(meta_facebook, "META_OAUTH_SCOPES", ["pages_show_list", "pages_manage_posts"])
    result = meta_facebook.start_flow()
    assert result["flow_id"]
    assert "dialog/oauth" in result["login_url"]
    assert "client_id=123" in result["login_url"]
    assert "pages_manage_posts" in result["login_url"]


def test_complete_flow_saves_page_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_facebook, "TOKENS_DIR", tmp_path)
    monkeypatch.setattr(meta_facebook, "ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr(meta_facebook, "_flows", {})

    captured = {}

    def fake_upsert(account):
        captured.update(account)
        return account

    monkeypatch.setattr("app.services.account_manager.upsert_account", fake_upsert)

    state = "test-state-123456789"
    meta_facebook._flows[state] = meta_facebook.FacebookOAuthFlow(
        state=state,
        created_at=meta_facebook.time(),
        user_access_token="user-token",
        pages=[{"id": "123", "name": "My Page", "access_token": "page-token"}],
    )

    result = meta_facebook.complete_flow(state, ["123"])
    assert result[0]["id"] == "fb_123"
    assert result[0]["external_id"] == "123"
    assert result[0]["configured"] is True
    assert captured["credential_ref"].startswith("meta_fb_123")

    credential_file = Path(tmp_path) / "meta_fb_123.json"
    data = credential_file.read_text(encoding="utf-8")
    assert "page-token" in data
