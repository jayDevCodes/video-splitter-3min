from __future__ import annotations

from pathlib import Path
from time import sleep, monotonic
from typing import Any

import httpx

from app.config import UPLOAD_POST_API_BASE, UPLOAD_POST_API_KEY

from .base import BasePlatformUploader, UploadResult


class FacebookUploader(BasePlatformUploader):
    platform = "facebook"

    def is_configured(self) -> bool:
        return bool(UPLOAD_POST_API_KEY)

    def _poll_request(self, request_id: str) -> dict[str, Any]:
        deadline = monotonic() + 20 * 60
        while monotonic() < deadline:
            response = httpx.get(
                f"{UPLOAD_POST_API_BASE.rstrip('/')}/api/uploadposts/status",
                headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}", "Accept": "application/json"},
                params={"request_id": request_id},
                timeout=30,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text[:500]}
            if response.status_code >= 400:
                raise RuntimeError(str(payload.get("message") or payload.get("error") or response.text[:500]))

            state = str(payload.get("status") or payload.get("state") or "").lower()
            if state in {"completed", "complete", "success", "succeeded", "published", "failed", "error"}:
                return payload
            sleep(2)
        raise RuntimeError("Timed out while waiting for the managed Facebook upload to finish.")

    def upload(self, video_path: Path, metadata: dict[str, Any]) -> UploadResult:
        account = metadata.get("_account") or {}
        profile = str(account.get("provider_profile") or "").strip()
        page_id = str(account.get("provider_page_id") or account.get("external_id") or "").strip()
        if not UPLOAD_POST_API_KEY:
            return UploadResult(status="not_configured", platform=self.platform, filename=video_path.name, error="Managed Facebook provider is not configured. Set UPLOAD_POST_API_KEY in .env.")
        if not profile or not page_id:
            return UploadResult(status="not_configured", platform=self.platform, filename=video_path.name, error="Facebook account is missing its managed provider profile or Page ID.")

        title_template = str(metadata.get("title_template") or "{filename} #{number}")
        title = title_template.replace("{filename}", video_path.stem).replace("{number}", str(metadata.get("_part_number", "")))
        description = str(metadata.get("description") or "")
        data = {
            "user": profile,
            "platform[]": "facebook",
            "title": title,
            "description": description,
            "facebook_page_id": page_id,
            "facebook_media_type": "REELS",
            "video_state": "PUBLISHED",
            "async_upload": "false",
            "external_id": f"{metadata.get('_folder_name', 'video')}:{video_path.name}:{page_id}",
        }

        try:
            with video_path.open("rb") as video_file:
                response = httpx.post(
                    f"{UPLOAD_POST_API_BASE.rstrip('/')}/api/upload",
                    headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}", "Accept": "application/json"},
                    data=data,
                    files={"video": (video_path.name, video_file, "video/mp4")},
                    timeout=300,
                )
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text[:500]}
            if response.status_code >= 400 or payload.get("success") is False:
                error = payload.get("message") or payload.get("error") or response.text[:500]
                return UploadResult(status="failed", platform=self.platform, filename=video_path.name, error=str(error))

            request_id = str(payload.get("request_id") or "").strip()
            if request_id and not ((payload.get("results") or {}).get("facebook") if isinstance(payload.get("results"), dict) else None):
                payload = self._poll_request(request_id)
        except Exception as exc:
            return UploadResult(status="failed", platform=self.platform, filename=video_path.name, error=str(exc))

        result = ((payload.get("results") or {}).get("facebook") or {}) if isinstance(payload, dict) else {}
        remote_id = None
        url = None
        if isinstance(result, dict):
            remote_id = result.get("post_id") or result.get("video_id") or result.get("id") or result.get("publish_id")
            url = result.get("url") or result.get("permalink")
        remote_id = str(remote_id or payload.get("request_id") or "") or None

        if isinstance(result, dict) and result.get("error"):
            return UploadResult(status="failed", platform=self.platform, filename=video_path.name, error=str(result["error"]))
        return UploadResult(status="uploaded", platform=self.platform, filename=video_path.name, url=str(url) if url else None, remote_id=remote_id)
