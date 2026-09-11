from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.metadata_manager import render_title
from app.services.thumbnail_manager import prepare_thumbnail
from app.services.youtube_auth import get_youtube_service

from .base import BasePlatformUploader, UploadResult


class YouTubeUploader(BasePlatformUploader):
    platform = "youtube"

    def upload(self, video_path: Path, metadata: dict[str, Any]) -> UploadResult:
        try:
            from googleapiclient.http import MediaFileUpload

            service = get_youtube_service()
            youtube = metadata.get("youtube", {})
            title = render_title(
                metadata.get("title_template", "{filename} #{number}"),
                number=int(metadata.get("_part_number", 0)),
                filename=str(metadata.get("_folder_name", "video")),
            )
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": metadata.get("description", "")[:5000],
                    "tags": metadata.get("tags", []),
                    "categoryId": str(youtube.get("category_id", "22")),
                },
                "status": {
                    "privacyStatus": youtube.get("privacy", "private"),
                    "selfDeclaredMadeForKids": bool(youtube.get("made_for_kids", False)),
                },
            }

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
            )
            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response["id"]
            thumbnail_status = "not_requested"
            thumbnail_name = metadata.get("thumbnail")
            if thumbnail_name:
                thumbnail_path = video_path.parent / thumbnail_name
                if thumbnail_path.exists():
                    try:
                        _, normalized = prepare_thumbnail(thumbnail_path, video_path.parent)
                        service.thumbnails().set(
                            videoId=video_id,
                            media_body=MediaFileUpload(str(normalized), mimetype="image/jpeg"),
                        ).execute()
                        thumbnail_status = "uploaded"
                    except Exception as exc:
                        thumbnail_status = f"failed: {exc}"

            return UploadResult(
                status="uploaded",
                platform=self.platform,
                filename=video_path.name,
                remote_id=video_id,
                url=f"https://youtu.be/{video_id}",
            )
        except Exception as exc:
            return UploadResult(
                status="failed",
                platform=self.platform,
                filename=video_path.name,
                error=str(exc),
            )
