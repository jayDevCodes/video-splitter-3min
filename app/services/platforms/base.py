from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UploadResult:
    status: str
    platform: str
    filename: str
    url: str | None = None
    remote_id: str | None = None
    error: str | None = None


class BasePlatformUploader:
    platform: str = "unknown"

    def is_configured(self) -> bool:
        return True

    def upload(self, video_path: Path, metadata: dict[str, Any]) -> UploadResult:
        raise NotImplementedError
