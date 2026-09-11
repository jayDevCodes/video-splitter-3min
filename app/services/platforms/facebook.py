from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BasePlatformUploader, UploadResult


class FacebookUploader(BasePlatformUploader):
    platform = "facebook"

    def is_configured(self) -> bool:
        return False

    def upload(self, video_path: Path, metadata: dict[str, Any]) -> UploadResult:
        return UploadResult(
            status="not_configured",
            platform=self.platform,
            filename=video_path.name,
            error="Facebook Page uploader is not configured yet. Add Meta OAuth/Page credentials before enabling it.",
        )
