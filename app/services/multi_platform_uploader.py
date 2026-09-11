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
from app.services.progress import progress_manager

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
    job_id: str | None = None,
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
    total = len(videos)

    def emit(event: str, **data: Any) -> None:
        if job_id:
            progress_manager.emit(job_id, event, **data)

    for clip_index, video_path in enumerate(videos, start=1):
        item_status = files_status.setdefault(video_path.name, {"targets": {}})
        target_status = item_status.setdefault("targets", {})
        target_ids = [a["id"] for a in accounts]
        already_complete = all(target_status.get(target_id, {}).get("status") == "uploaded" for target_id in target_ids)
        if already_complete:
            emit("clip_skipped", task="upload", clip=video_path.name, clip_index=clip_index, clip_total=total, reason="already_uploaded")
            continue

        if last_clip_finished is not None and gap_seconds:
            remaining = max(0, int(gap_seconds - (time.monotonic() - last_clip_finished)))
            if remaining:
                emit("gap_started", task="waiting", clip=video_path.name, clip_index=clip_index, clip_total=total, status="waiting", progress=0, remaining_seconds=remaining)
                while remaining > 0:
                    emit("gap_tick", task="waiting", clip=video_path.name, clip_index=clip_index, clip_total=total, status="waiting", progress=100 - int((remaining / gap_seconds) * 100), remaining_seconds=remaining)
                    time.sleep(1)
                    remaining = max(0, int(gap_seconds - (time.monotonic() - last_clip_finished)))
                emit("gap_completed", task="waiting", clip=video_path.name, clip_index=clip_index, clip_total=total, status="completed", progress=100, remaining_seconds=0)

        emit("clip_started", task="clip_upload", clip=video_path.name, clip_index=clip_index, clip_total=total, status="running", progress=0)
        clip_result: dict[str, Any] = {"filename": video_path.name, "targets": {}}
        failed = False

        for account in accounts:
            account_id = account["id"]
            current = target_status.get(account_id, {})
            if current.get("status") == "uploaded":
                clip_result["targets"][account_id] = current
                emit("account_skipped", task=f"{account['platform']}_upload", platform=account["platform"], account_id=account_id, account_name=account["name"], clip=video_path.name, status="completed", progress=100, reason="already_uploaded")
                continue

            platform = account["platform"]
            task = f"{platform}_upload"
            emit("account_upload_started", task=task, platform=platform, account_id=account_id, account_name=account["name"], clip=video_path.name, clip_index=clip_index, clip_total=total, status="running", progress=0, indeterminate=True)
            uploader_cls = PLATFORM_BUILDERS[platform]
            uploader = uploader_cls()
            upload_metadata = {
                **metadata,
                "_part_number": part_number(video_path),
                "_folder_name": output_dir.name,
                "_account": account,
            }
            try:
                result: UploadResult = uploader.upload(video_path, upload_metadata)
            except Exception as exc:
                result = UploadResult(status="failed", url=None, remote_id=None, error=str(exc))

            saved = {
                "status": result.status,
                "platform": platform,
                "account_id": account_id,
                "account_name": account["name"],
                "url": result.url,
                "remote_id": result.remote_id,
                "error": result.error,
            }
            target_status[account_id] = saved
            clip_result["targets"][account_id] = saved
            if result.status == "uploaded":
                emit("account_upload_completed", task=task, platform=platform, account_id=account_id, account_name=account["name"], clip=video_path.name, status="completed", progress=100, url=result.url)
            else:
                failed = True
                emit("account_upload_failed", task=task, platform=platform, account_id=account_id, account_name=account["name"], clip=video_path.name, status="failed", progress=100, error=result.error or "Upload failed")

        save_status(output_dir, status)
        results.append(clip_result)

        if failed:
            emit("clip_failed", task="clip_upload", clip=video_path.name, clip_index=clip_index, clip_total=total, status="failed", progress=100)
            break

        last_clip_finished = time.monotonic()
        emit("clip_completed", task="clip_upload", clip=video_path.name, clip_index=clip_index, clip_total=total, status="completed", progress=100)
        if all(target_status.get(account["id"], {}).get("status") == "uploaded" for account in accounts):
            if delete_after_upload and video_path.exists():
                video_path.unlink()
                item_status["deleted"] = True
                save_status(output_dir, status)
                emit("clip_deleted", task="cleanup", clip=video_path.name, status="completed", progress=100)

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
