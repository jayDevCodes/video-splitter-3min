from pathlib import Path
import math
import subprocess
from app.config import FFMPEG_BIN
from app.models.video import VideoInfo


OUTPUT_SIZES = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
}


def split_video(
    input_path: Path,
    output_dir: Path,
    info: VideoInfo,
    chunk_seconds: int = 180,
    orientation: str = "vertical",
) -> list[Path]:
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than zero")
    if orientation not in OUTPUT_SIZES:
        raise ValueError("orientation must be 'vertical' or 'horizontal'")

    width, height = OUTPUT_SIZES[orientation]
    parts = max(1, math.ceil(info.duration / chunk_seconds))
    created: list[Path] = []

    for index in range(parts):
        start = index * chunk_seconds
        remaining = max(0.0, info.duration - start)
        duration = min(chunk_seconds, remaining)
        if duration <= 0.05:
            continue

        output_path = output_dir / f"part_{index + 1:03d}.mp4"
        # Scale while preserving aspect ratio, then crop any excess to the
        # exact target frame. This avoids stretching faces or objects.
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase:"
            f"force_divisible_by=2,crop={width}:{height}"
        )
        command = [
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel", "error",
            "-ss", f"{start:.3f}",
            "-i", str(input_path),
            "-t", f"{duration:.3f}",
            "-map", "0:v:0",
            "-map", "0:a?",
            "-vf", vf,
            "-sws_flags", "lanczos",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            for path in created:
                path.unlink(missing_ok=True)
            raise RuntimeError(result.stderr.strip() or f"FFmpeg failed on part {index + 1}.")
        created.append(output_path)

    return created
