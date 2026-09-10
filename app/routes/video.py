from pathlib import Path
import asyncio
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from app.config import DEFAULT_CHUNK_SECONDS, MAX_UPLOAD_MB, OUTPUT_DIR
from app.models.video import SplitResponse
from app.services.file_manager import cleanup_file, make_output_directory, save_upload
from app.services.metadata_manager import is_ready, mark_ready
from app.services.video_analyzer import probe_video
from app.services.video_splitter import OUTPUT_SIZES, split_video

router = APIRouter(prefix="/api/video", tags=["video"])


def _validate_upload_size(path: Path) -> None:
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    size = path.stat().st_size
    if size > max_bytes:
        cleanup_file(path)
        raise HTTPException(status_code=413, detail=f"Video exceeds the {MAX_UPLOAD_MB} MB upload limit.")


def _safe_output_dir(output_directory: str) -> Path:
    raw = Path(output_directory)
    candidate = (OUTPUT_DIR / raw).resolve() if not raw.is_absolute() else raw.resolve()
    root = OUTPUT_DIR.resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid output directory.")
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Output folder not found.")
    return candidate


@router.post("/split", response_model=SplitResponse)
async def split_uploaded_video(
    file: UploadFile = File(...),
    chunk_seconds: int = DEFAULT_CHUNK_SECONDS,
    orientation: str = Query("vertical", description="Output format: vertical or horizontal"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a video file.")
    if chunk_seconds <= 0 or chunk_seconds > 3600:
        raise HTTPException(status_code=400, detail="chunk_seconds must be between 1 and 3600 seconds.")
    if orientation not in OUTPUT_SIZES:
        raise HTTPException(status_code=400, detail="orientation must be 'vertical' or 'horizontal'.")

    input_path = None
    try:
        input_path = await asyncio.to_thread(save_upload, file, file.filename)
        _validate_upload_size(input_path)
        info = await asyncio.to_thread(probe_video, input_path)
        output_dir = await asyncio.to_thread(make_output_directory, file.filename)
        parts = await asyncio.to_thread(
            split_video, input_path, output_dir, info, chunk_seconds, orientation
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


@router.get("/status")
def generation_status(output_directory: str):
    output_dir = _safe_output_dir(output_directory)
    parts = sorted(output_dir.glob("part_*.mp4"))
    return {
        "ready": is_ready(output_dir),
        "output_directory": output_directory,
        "parts_created": len(parts),
        "parts": [p.name for p in parts],
    }
