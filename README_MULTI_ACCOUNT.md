# Multi-account upload architecture

Old Upload now works with explicit account targets instead of only platform names.

Each job stores target account IDs, not credentials. Example:

```json
{
  "targets": [
    {"account_id": "yt_001", "platform": "youtube"},
    {"account_id": "yt_002", "platform": "youtube"},
    {"account_id": "fb_001", "platform": "facebook"},
    {"account_id": "ig_001", "platform": "instagram"}
  ],
  "gap_seconds": 60
}
```

Processing order is clip-first:

`part_001 -> all selected accounts -> mandatory gap -> part_002 -> ...`

A clip is not deleted until every selected target succeeds. Per-account status is persisted in `_config/upload_status.json`, while job configuration is persisted in `_config/upload_job.json`.

Account definitions are stored locally in `tokens/accounts.json`. YouTube accounts can use separate token files such as `tokens/youtube_<account-id>.json`. Credentials and token files are ignored by Git.

Facebook and Instagram are currently registry/UI-ready but their real Meta publishing adapters remain unconfigured until Meta OAuth/Page/Professional Account credentials are supplied.
