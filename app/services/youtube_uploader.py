from __future__ import annotations

import re
from pathlib import Path

from app.services.metadata_manager import load_metadata, load_status, render_title, save_status
from app.services.youtube_auth import get_youtube_service

VIDEO_RE = re.compile(r"part_(\d+)\.mp4$", re.IGNORECASE)


def _part_number(path: Path) -> int:
    match = VIDEO_RE.match(path.name)
    return int(match.group(1)) if match else 999999


def upload_pending_folder(output_dir: Path) -> list[dict]:
    metadata = load_metadata(output_dir)
    upload_config = metadata.get("upload", {})
    if not upload_config.get("enabled", True) or not upload_config.get("auto_upload", False):
        return []

    status = load_status(output_dir)
    files_status = status.setdefault("files", {})
    videos = sorted(output_dir.glob("part_*.mp4"), key=_part_number)
    pending = [p for p in videos if files_status.get(p.name, {}).get("status") != "uploaded"]
    if not pending:
        return []

    service = get_youtube_service()
    results = []
    snippet = metadata.get("youtube", {})
    thumbnail_name = metadata.get("thumbnail")
    thumbnail_path = output_dir / thumbnail_name if thumbnail_name else None

    for video_path in pending:
        number = _part_number(video_path)
        title = render_title(
            metadata.get("title_template", "{filename} #{number}"),
            number=number,
            filename=output_dir.name,
        )
        body = {
            "snippet": {
                "title": title[:100],
                "description": metadata.get("description", "")[:5000],
                "tags": metadata.get("tags", []),
                "categoryId": str(snippet.get("category_id", "22")),
            },
            "status": {
                "privacyStatus": snippet.get("privacy", "private"),
                "selfDeclaredMadeForKids": bool(snippet.get("made_for_kids", False)),
            },
        }

        try:
            from googleapiclient.http import MediaFileUpload

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
            )
            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response["id"]
            if thumbnail_path and thumbnail_path.exists():
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path)),
                ).execute()

            item = {
                "status": "uploaded",
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
            }
            files_status[video_path.name] = item
            results.append({"filename": video_path.name, **item})
            save_status(output_dir, status)
        except Exception as exc:
            item = {"status": "failed", "error": str(exc)}
            files_status[video_path.name] = item
            save_status(output_dir, status)
            results.append({"filename": video_path.name, **item})

    return results
