from pathlib import Path
import asyncio
import json
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from app.config import DEFAULT_CHUNK_SECONDS, MAX_UPLOAD_MB
from app.models.video import SplitResponse
from app.services.file_manager import cleanup_file, make_output_directory, save_upload
from app.services.metadata_manager import mark_ready, write_metadata
from app.services.video_analyzer import probe_video
from app.services.video_splitter import OUTPUT_SIZES, split_video

router = APIRouter(prefix="/api/video", tags=["video"])


def _validate_upload_size(path: Path) -> None:
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    size = path.stat().st_size
    if size > max_bytes:
        cleanup_file(path)
        raise HTTPException(status_code=413, detail=f"Video exceeds the {MAX_UPLOAD_MB} MB upload limit.")


@router.post("/split", response_model=SplitResponse)
async def split_uploaded_video(
    file: UploadFile = File(...),
    chunk_seconds: int = DEFAULT_CHUNK_SECONDS,
    orientation: str = Query("vertical", description="Output format: vertical or horizontal"),
    title_template: str = Form("{filename} #{number}"),
    description: str = Form(""),
    tags: str = Form("shorts,youtube"),
    privacy: str = Form("private"),
    category_id: str = Form("22"),
    made_for_kids: bool = Form(False),
    auto_upload: bool = Form(False),
    thumbnail: UploadFile | None = File(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a video file.")
    if chunk_seconds <= 0 or chunk_seconds > 3600:
        raise HTTPException(status_code=400, detail="chunk_seconds must be between 1 and 3600 seconds.")
    if orientation not in OUTPUT_SIZES:
        raise HTTPException(status_code=400, detail="orientation must be 'vertical' or 'horizontal'.")
    if privacy not in {"private", "unlisted", "public"}:
        raise HTTPException(status_code=400, detail="privacy must be private, unlisted, or public.")

    input_path = None
    thumbnail_path = None
    try:
        input_path = await asyncio.to_thread(save_upload, file, file.filename)
        _validate_upload_size(input_path)
        info = await asyncio.to_thread(probe_video, input_path)
        output_dir = await asyncio.to_thread(make_output_directory, file.filename)
        parts = await asyncio.to_thread(
            split_video, input_path, output_dir, info, chunk_seconds, orientation
        )

        thumbnail_name = None
        if thumbnail and thumbnail.filename:
            suffix = Path(thumbnail.filename).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png"}:
                raise HTTPException(status_code=400, detail="Thumbnail must be JPG, JPEG, or PNG.")
            thumbnail_name = f"thumbnail{suffix}"
            thumbnail_path = output_dir / thumbnail_name
            with thumbnail_path.open("wb") as target:
                await asyncio.to_thread(__import__("shutil").copyfileobj, thumbnail.file, target)

        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        await asyncio.to_thread(
            write_metadata,
            output_dir,
            title_template=title_template,
            description=description,
            tags=tag_list,
            thumbnail=thumbnail_name,
            privacy=privacy,
            category_id=category_id,
            made_for_kids=made_for_kids,
            auto_upload=auto_upload,
        )
        await asyncio.to_thread(mark_ready, output_dir)

        return SplitResponse(
            source_filename=file.filename,
            output_directory=str(output_dir.relative_to(output_dir.parents[1])),
            total_duration=info.duration,
            chunk_seconds=chunk_seconds,
            parts_created=len(parts),
            parts=[p.name for p in parts],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if input_path:
            cleanup_file(input_path)
