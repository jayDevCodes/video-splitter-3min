from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.services.account_manager import resolve_targets
from app.services.metadata_manager import load_status, save_status
from app.services.platforms.base import UploadResult
from app.services.platforms.facebook import FacebookUploader
from app.services.platforms.instagram import InstagramUploader
from app.services.platforms.youtube import YouTubeUploader

VIDEO_RE = __import__("re").compile(r"part_(\d+)\.mp4$", __import__("re").IGNORECASE)
PLATFORM_BUILDERS = {"youtube": YouTubeUploader, "facebook": FacebookUploader, "instagram": InstagramUploader}


def part_number(path: Path) -> int:
    match = VIDEO_RE.match(path.name)
    return int(match.group(1)) if match else 999999


def run_multi_platform_upload(
    output_dir: Path,
    *,
    targets: list[dict[str, str]],
    metadata: dict[str, Any],
    gap_seconds: int,
    delete_after_upload: bool,
) -> dict[str, Any]:
    accounts = resolve_targets(targets)
    if gap_seconds < 0 or gap_seconds > 86400:
        raise ValueError("gap_seconds must be between 0 and 86400 seconds.")

    status = load_status(output_dir)
    files_status = status.setdefault("files", {})
    job = status.setdefault("upload_job", {})
    job.update({"targets": [{"account_id": a["id"], "platform": a["platform"], "name": a["name"]} for a in accounts], "gap_seconds": gap_seconds})

    videos = sorted(output_dir.glob("part_*.mp4"), key=part_number)
    results: list[dict[str, Any]] = []
    last_clip_finished: float | None = None

    for video_path in videos:
        item_status = files_status.setdefault(video_path.name, {"targets": {}})
        target_status = item_status.setdefault("targets", {})
        target_ids = [a["id"] for a in accounts]
        already_complete = all(target_status.get(target_id, {}).get("status") == "uploaded" for target_id in target_ids)
        if already_complete:
            continue

        if last_clip_finished is not None and gap_seconds:
            time.sleep(max(0.0, gap_seconds - (time.monotonic() - last_clip_finished)))

        clip_result: dict[str, Any] = {"filename": video_path.name, "targets": {}}
        failed = False

        for account in accounts:
            account_id = account["id"]
            current = target_status.get(account_id, {})
            if current.get("status") == "uploaded":
                clip_result["targets"][account_id] = current
                continue

            uploader_cls = PLATFORM_BUILDERS[account["platform"]]
            uploader = uploader_cls()
            upload_metadata = {
                **metadata,
                "_part_number": part_number(video_path),
                "_folder_name": output_dir.name,
                "_account": account,
            }
            result: UploadResult = uploader.upload(video_path, upload_metadata)
            saved = {
                "status": result.status,
                "platform": account["platform"],
                "account_id": account_id,
                "account_name": account["name"],
                "url": result.url,
                "remote_id": result.remote_id,
                "error": result.error,
            }
            target_status[account_id] = saved
            clip_result["targets"][account_id] = saved
            if result.status != "uploaded":
                failed = True

        save_status(output_dir, status)
        results.append(clip_result)

        if failed:
            break

        last_clip_finished = time.monotonic()
        if all(target_status.get(account["id"], {}).get("status") == "uploaded" for account in accounts):
            if delete_after_upload and video_path.exists():
                video_path.unlink()
                item_status["deleted"] = True
                save_status(output_dir, status)

    remaining = len(list(output_dir.glob("part_*.mp4")))
    return {
        "output_directory": str(output_dir),
        "targets": [{"id": a["id"], "platform": a["platform"], "name": a["name"]} for a in accounts],
        "gap_seconds": gap_seconds,
        "delete_after_upload": delete_after_upload,
        "processed": len(results),
        "remaining_files": remaining,
        "results": results,
        "stopped_on_error": bool(results and any(any(x.get("status") != "uploaded" for x in item.get("targets", {}).values()) for item in results)),
    }
