from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile, File

from app.config import OUTPUT_DIR
from app.services.account_manager import get_accounts_by_platform, resolve_targets
from app.services.jobs.job_manager import job_manager
from app.services.metadata_manager import load_metadata
from app.services.upload.runner import run_upload_job
from app.services.upload_manager import discover_upload_folders, folder_summary

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _safe_output_dir(output_directory: str) -> Path:
    raw = Path(output_directory)
    root = OUTPUT_DIR.resolve()
    candidate = raw.resolve() if raw.is_absolute() else (OUTPUT_DIR.parent / raw if raw.parts and raw.parts[0] == OUTPUT_DIR.name else OUTPUT_DIR / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid output directory.")
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Output folder not found.")
    return candidate


@router.get("/targets")
def upload_targets():
    return {"accounts": get_accounts_by_platform()}


@router.get("/platforms")
def platform_capabilities():
    accounts = get_accounts_by_platform()
    return {
        "platforms": [
            {"id": platform, "name": label, "configured": any(a.get("configured", False) for a in accounts.get(platform, [])), "accounts": accounts.get(platform, [])}
            for platform, label in (("youtube", "YouTube Shorts"), ("facebook", "Facebook Page"), ("instagram", "Instagram Reels"))
        ]
    }


@router.get("/folders")
def list_folders():
    return {"folders": discover_upload_folders(OUTPUT_DIR)}


@router.get("/folder")
def get_folder(output_directory: str):
    directory = _safe_output_dir(output_directory)
    summary = folder_summary(directory)
    try:
        metadata = load_metadata(directory)
    except FileNotFoundError:
        metadata = {}
    job_path = directory / "_config" / "upload_job.json"
    job = json.loads(job_path.read_text(encoding="utf-8")) if job_path.exists() else {}
    return {**summary, "metadata": metadata, "upload_job": job}


@router.post("/start")
def start_upload(
    background_tasks: BackgroundTasks,
    output_directory: str = Form(...),
    targets: str = Form(...),
    title_template: str = Form("{filename} #{number}"),
    description: str = Form(""),
    tags: str = Form("shorts,youtube"),
    privacy: str = Form("private"),
    category_id: str = Form("22"),
    made_for_kids: bool = Form(False),
    gap_seconds: int = Form(60),
    delete_after_upload: bool = Form(True),
    thumbnail: UploadFile | None = File(None),
):
    directory = _safe_output_dir(output_directory)
    try:
        target_list = json.loads(targets)
        if not isinstance(target_list, list):
            raise ValueError("targets must be a JSON array")
        accounts = resolve_targets(target_list)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if privacy not in {"private", "unlisted", "public"}:
        raise HTTPException(status_code=400, detail="privacy must be private, unlisted, or public.")
    if gap_seconds < 0 or gap_seconds > 86400:
        raise HTTPException(status_code=400, detail="gap_seconds must be between 0 and 86400 seconds.")

    if thumbnail and thumbnail.filename:
        suffix = Path(thumbnail.filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Thumbnail must be JPG, JPEG, PNG, or WEBP.")
        target = directory / f"_thumbnail_source{suffix}"
        with target.open("wb") as output:
            import shutil
            shutil.copyfileobj(thumbnail.file, output)

    metadata = {
        "title_template": title_template.strip() or "{filename} #{number}",
        "description": description,
        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
        "thumbnail": None,
        "youtube": {"privacy": privacy, "category_id": category_id, "made_for_kids": made_for_kids},
        "upload": {"enabled": True, "gap_seconds": gap_seconds, "delete_after_upload": delete_after_upload},
    }

    job_path = directory / "_config" / "upload_job.json"
    job_path.parent.mkdir(parents=True, exist_ok=True)
    target_snapshot = [{"account_id": a["id"], "platform": a["platform"], "name": a["name"]} for a in accounts]
    job_id = job_manager.create(
        "upload",
        {
            "output_directory": str(directory),
            "targets": target_snapshot,
            "gap_seconds": gap_seconds,
        },
    )
    job_path.write_text(json.dumps({
        "status": "queued",
        "job_id": job_id,
        "targets": target_snapshot,
        "gap_seconds": gap_seconds,
        "gap_rule": "minimum delay starts after every selected account finishes the previous clip",
        "delete_after_upload": delete_after_upload,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    background_tasks.add_task(
        run_upload_job,
        job_id,
        directory,
        targets=target_list,
        metadata=metadata,
        gap_seconds=gap_seconds,
        delete_after_upload=delete_after_upload,
        job_path=job_path,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "targets": target_snapshot,
        "gap_seconds": gap_seconds,
        "message": "Upload job queued. Subscribe to the live job events stream for progress.",
    }
