from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.services.metadata_manager import load_status, save_status
from app.services.platforms.base import UploadResult
from app.services.platforms.facebook import FacebookUploader
from app.services.platforms.instagram import InstagramUploader
from app.services.platforms.youtube import YouTubeUploader

VIDEO_RE = __import__("re").compile(r"part_(\d+)\.mp4$", __import__("re").IGNORECASE)


PLATFORM_BUILDERS = {
    "youtube": YouTubeUploader,
    "facebook": FacebookUploader,
    "instagram": InstagramUploader,
}


def part_number(path: Path) -> int:
    match = VIDEO_RE.match(path.name)
    return int(match.group(1)) if match else 999999


def validate_platforms(platforms: list[str]) -> list[str]:
    cleaned = []
    for platform in platforms:
        value = str(platform).strip().lower()
        if value not in PLATFORM_BUILDERS:
            raise ValueError(f"Unsupported platform: {value}")
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        raise ValueError("Select at least one upload platform.")
    return cleaned


def run_multi_platform_upload(
    output_dir: Path,
    *,
    platforms: list[str],
    metadata: dict[str, Any],
    gap_seconds: int,
    delete_after_upload: bool,
) -> dict[str, Any]:
    platforms = validate_platforms(platforms)
    if gap_seconds < 0 or gap_seconds > 86400:
        raise ValueError("gap_seconds must be between 0 and 86400 seconds.")

    status = load_status(output_dir)
    files_status = status.setdefault("files", {})
    videos = sorted(output_dir.glob("part_*.mp4"), key=part_number)
    results: list[dict[str, Any]] = []
    last_clip_finished: float | None = None

    for video_path in videos:
        if video_path.name not in files_status:
            files_status[video_path.name] = {"platforms": {}}

        item_status = files_status[video_path.name]
        platform_status = item_status.setdefault("platforms", {})
        already_complete = all(platform_status.get(p, {}).get("status") == "uploaded" for p in platforms)
        if already_complete:
            continue

        # Hard clip boundary: the configured delay starts only after the previous
        # clip has finished processing on every selected platform. It cannot be
        # skipped by a slow/fast previous upload.
        if last_clip_finished is not None and gap_seconds:
            time.sleep(max(0.0, gap_seconds - (time.monotonic() - last_clip_finished)))

        clip_result: dict[str, Any] = {"filename": video_path.name, "platforms": {}}
        failed = False
        for platform in platforms:
            current = platform_status.get(platform, {})
            if current.get("status") == "uploaded":
                clip_result["platforms"][platform] = current
                continue

            uploader = PLATFORM_BUILDERS[platform]()
            upload_metadata = {
                **metadata,
                "_part_number": part_number(video_path),
                "_folder_name": output_dir.name,
            }
            result: UploadResult = uploader.upload(video_path, upload_metadata)
            saved = {
                "status": result.status,
                "url": result.url,
                "remote_id": result.remote_id,
                "error": result.error,
            }
            platform_status[platform] = saved
            clip_result["platforms"][platform] = saved
            if result.status != "uploaded":
                failed = True

        save_status(output_dir, status)
        results.append(clip_result)

        if failed:
            # Do not silently advance to the next clip. Retry/repair the current
            # clip first so the inter-clip gap remains a real enforced boundary.
            break

        last_clip_finished = time.monotonic()
        all_selected_uploaded = all(
            platform_status.get(platform, {}).get("status") == "uploaded"
            for platform in platforms
        )
        if all_selected_uploaded and delete_after_upload and video_path.exists():
            video_path.unlink()
            item_status["deleted"] = True
            save_status(output_dir, status)

    remaining = len(list(output_dir.glob("part_*.mp4")))
    return {
        "output_directory": str(output_dir),
        "platforms": platforms,
        "gap_seconds": gap_seconds,
        "delete_after_upload": delete_after_upload,
        "processed": len(results),
        "remaining_files": remaining,
        "stopped_on_error": bool(results and any(
            any(x.get("status") != "uploaded" for x in item.get("platforms", {}).values())
            for item in results
        )),
        "results": results,
    }
