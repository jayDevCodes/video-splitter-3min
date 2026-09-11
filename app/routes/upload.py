from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from app.config import OUTPUT_DIR
from app.services.metadata_manager import load_metadata
from app.services.multi_platform_uploader import run_multi_platform_upload, validate_platforms
from app.services.upload_manager import discover_upload_folders, folder_summary
from app.services.youtube_auth import get_youtube_service

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


@router.get("/platforms")
def platform_capabilities():
    return {
        "platforms": [
            {"id": "youtube", "name": "YouTube Shorts", "configured": True},
            {"id": "facebook", "name": "Facebook Page", "configured": False},
            {"id": "instagram", "name": "Instagram Reels", "configured": False},
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
    return {**summary, "metadata": metadata}


@router.post("/start")
def start_upload(
    output_directory: str = Form(...),
    platforms: str = Form("youtube"),
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
        selected = validate_platforms([item for item in platforms.split(",") if item.strip()])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if privacy not in {"private", "unlisted", "public"}:
        raise HTTPException(status_code=400, detail="privacy must be private, unlisted, or public.")
    if gap_seconds < 0 or gap_seconds > 86400:
        raise HTTPException(status_code=400, detail="gap_seconds must be between 0 and 86400 seconds.")

    # Thumbnail remains compatible with the existing folder-level YouTube flow.
    # Other platforms can consume the same folder thumbnail when their adapters are enabled.
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
        "youtube": {
            "privacy": privacy,
            "category_id": category_id,
            "made_for_kids": made_for_kids,
        },
        "upload": {
            "enabled": True,
            "gap_seconds": gap_seconds,
            "delete_after_upload": delete_after_upload,
        },
    }

    result = run_multi_platform_upload(
        directory,
        platforms=selected,
        metadata=metadata,
        gap_seconds=gap_seconds,
        delete_after_upload=delete_after_upload,
    )
    return result
