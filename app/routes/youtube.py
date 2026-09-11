from pathlib import Path
import re
import time
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.config import OUTPUT_DIR
from app.services.metadata_manager import load_metadata, load_status, render_title, save_status, write_metadata
from app.services.thumbnail_manager import prepare_thumbnail
from app.services.upload_manager import discover_upload_folders, folder_summary
from app.services.youtube_auth import get_youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
VIDEO_RE = re.compile(r"part_(\d+)\.mp4$", re.IGNORECASE)


def _part_number(path: Path) -> int:
    match = VIDEO_RE.match(path.name)
    return int(match.group(1)) if match else 999999


def _safe_output_dir(output_directory: str) -> Path:
    raw = Path(output_directory)
    root = OUTPUT_DIR.resolve()
    if raw.is_absolute():
        candidate = raw.resolve()
    elif raw.parts and raw.parts[0] == OUTPUT_DIR.name:
        candidate = (OUTPUT_DIR.parent / raw).resolve()
    else:
        candidate = (OUTPUT_DIR / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid output directory.")
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Output folder not found.")
    return candidate


@router.get("/folders")
def list_upload_folders():
    return {"folders": discover_upload_folders(OUTPUT_DIR)}


@router.get("/folder")
def get_upload_folder(output_directory: str):
    output_dir = _safe_output_dir(output_directory)
    summary = folder_summary(output_dir)
    try:
        metadata = load_metadata(output_dir)
    except FileNotFoundError:
        metadata = {}
    saved_thumbnail = metadata.get("thumbnail") if metadata else None
    thumbnail_path = output_dir / saved_thumbnail if saved_thumbnail else None
    return {
        **summary,
        "metadata": metadata,
        "saved_thumbnail": saved_thumbnail if thumbnail_path and thumbnail_path.exists() else None,
    }


@router.get("/prepare")
def prepare_upload(output_directory: str):
    output_dir = _safe_output_dir(output_directory)
    return folder_summary(output_dir)


@router.post("/upload")
def upload_to_youtube(
    output_directory: str = Form(...),
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
    if privacy not in {"private", "unlisted", "public"}:
        raise HTTPException(status_code=400, detail="privacy must be private, unlisted, or public.")
    if gap_seconds < 0 or gap_seconds > 86400:
        raise HTTPException(status_code=400, detail="gap_seconds must be between 0 and 86400 seconds.")

    output_dir = _safe_output_dir(output_directory)
    videos = sorted(output_dir.glob("part_*.mp4"), key=_part_number)
    if not videos:
        raise HTTPException(status_code=400, detail="No generated Shorts found in this folder.")

    try:
        existing_metadata = load_metadata(output_dir)
    except FileNotFoundError:
        existing_metadata = {}

    saved_thumbnail_name = existing_metadata.get("thumbnail")
    thumbnail_path = output_dir / saved_thumbnail_name if saved_thumbnail_name else None

    if thumbnail and thumbnail.filename:
        suffix = Path(thumbnail.filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Thumbnail must be JPG, JPEG, PNG, or WEBP.")
        try:
            temp_thumbnail = output_dir / f"._thumbnail_source{suffix}"
            with temp_thumbnail.open("wb") as target:
                import shutil
                shutil.copyfileobj(thumbnail.file, target)
            thumbnail_name, thumbnail_path = prepare_thumbnail(temp_thumbnail, output_dir)
            temp_thumbnail.unlink(missing_ok=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Thumbnail could not be prepared: {exc}") from exc
    elif thumbnail_path and thumbnail_path.exists():
        try:
            thumbnail_name, thumbnail_path = prepare_thumbnail(thumbnail_path, output_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Saved thumbnail could not be prepared: {exc}") from exc
    else:
        thumbnail_name = None
        thumbnail_path = None

    tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    metadata_path = write_metadata(
        output_dir,
        title_template=title_template,
        description=description,
        tags=tags_list,
        thumbnail=thumbnail_name,
        privacy=privacy,
        category_id=category_id,
        made_for_kids=made_for_kids,
        auto_upload=False,
        gap_seconds=gap_seconds,
        delete_after_upload=delete_after_upload,
    )

    status = load_status(output_dir)
    files_status = status.setdefault("files", {})
    pending = [p for p in videos if files_status.get(p.name, {}).get("status") != "uploaded"]
    if not pending:
        return {"output_directory": output_directory, "total_requested": 0, "processed": 0, "remaining_files": 0, "results": []}

    service = get_youtube_service()
    from googleapiclient.http import MediaFileUpload

    results = []
    last_upload_finished = None
    for index, video_path in enumerate(pending):
        if last_upload_finished is not None and gap_seconds:
            elapsed = time.monotonic() - last_upload_finished
            remaining_gap = max(0.0, gap_seconds - elapsed)
            if remaining_gap:
                time.sleep(remaining_gap)

        number = _part_number(video_path)
        title = render_title(title_template, number=number, filename=output_dir.name)
        body = {
            "snippet": {"title": title[:100], "description": description[:5000], "tags": tags_list, "categoryId": str(category_id)},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids},
        }
        try:
            request = service.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True))
            response = None
            while response is None:
                _, response = request.next_chunk()
            video_id = response["id"]

            thumbnail_status = "not_requested"
            if thumbnail_path and thumbnail_path.exists():
                last_thumbnail_error = None
                for attempt in range(4):
                    try:
                        service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")).execute()
                        thumbnail_status = "uploaded"
                        last_thumbnail_error = None
                        break
                    except Exception as exc:
                        last_thumbnail_error = exc
                        if attempt < 3:
                            time.sleep(5 * (attempt + 1))
                if last_thumbnail_error is not None and thumbnail_status != "uploaded":
                    thumbnail_status = f"failed: {last_thumbnail_error}"

            item = {"status": "uploaded", "video_id": video_id, "url": f"https://youtu.be/{video_id}", "deleted": False, "thumbnail_status": thumbnail_status}
            if delete_after_upload and video_path.exists():
                video_path.unlink()
                item["deleted"] = True
            files_status[video_path.name] = item
            results.append({"filename": video_path.name, **item})
            save_status(output_dir, status)
            last_upload_finished = time.monotonic()
        except Exception as exc:
            item = {"status": "failed", "error": str(exc)}
            files_status[video_path.name] = item
            save_status(output_dir, status)
            results.append({"filename": video_path.name, **item})
            break

    remaining = len(list(output_dir.glob("part_*.mp4")))
    return {"output_directory": output_directory, "total_requested": len(pending), "processed": len(results), "remaining_files": remaining, "stopped_on_error": any(item.get("status") == "failed" for item in results), "results": results, "metadata_saved": str(metadata_path.relative_to(output_dir))}
