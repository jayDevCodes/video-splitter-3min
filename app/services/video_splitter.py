from __future__ import annotations

import math
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.config import FFMPEG_BIN
from app.models.video import VideoInfo
from app.services.text_overlay import create_short_overlay


OUTPUT_SIZES = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
    "vertical_full_frame": (1080, 1920),
}


def _build_video_filter(width: int, height: int, orientation: str) -> str:
    if orientation == "vertical_full_frame":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
        )

    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase:"
        f"force_divisible_by=2,crop={width}:{height}"
    )


def _run_ffmpeg(
    command: list[str],
    part_number: int,
) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error = result.stderr.strip() or f"FFmpeg failed on part {part_number}."
        raise RuntimeError(error)


def split_video(
    input_path: Path,
    output_dir: Path,
    info: VideoInfo,
    chunk_seconds: int = 180,
    orientation: str = "vertical",
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> list[Path]:
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than zero")
    if orientation not in OUTPUT_SIZES:
        raise ValueError(
            "orientation must be 'vertical', 'horizontal', or 'vertical_full_frame'"
        )

    width, height = OUTPUT_SIZES[orientation]
    parts = max(1, math.ceil(info.duration / chunk_seconds))
    created: list[Path] = []

    for index in range(parts):
        start = index * chunk_seconds
        remaining = max(0.0, info.duration - start)
        duration = min(chunk_seconds, remaining)
        if duration <= 0.05:
            continue

        part_number = index + 1
        output_path = output_dir / f"part_{part_number:03d}.mp4"
        if progress_callback:
            progress_callback("part_started", part_number, parts)

        base_filter = _build_video_filter(width, height, orientation)
        command = [
            FFMPEG_BIN,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(input_path),
            "-t",
            f"{duration:.3f}",
        ]

        overlay_path: Path | None = None
        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        try:
            if orientation == "vertical_full_frame":
                temp_dir = tempfile.TemporaryDirectory(prefix="video-splitter-overlay-")
                overlay_path = create_short_overlay(
                    Path(temp_dir.name) / "text_overlay.png",
                    part_number=part_number,
                )
                filter_complex = (
                    f"[0:v]{base_filter}[base];"
                    f"[1:v]format=rgba[overlay];"
                    f"[base][overlay]overlay=0:0:shortest=1[v]"
                )
                command.extend(
                    [
                        "-loop",
                        "1",
                        "-i",
                        str(overlay_path),
                        "-filter_complex",
                        filter_complex,
                        "-map",
                        "[v]",
                        "-map",
                        "0:a?",
                    ]
                )
            else:
                command.extend(
                    [
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a?",
                        "-vf",
                        base_filter,
                    ]
                )

            command.extend(
                [
                    "-sws_flags",
                    "lanczos",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    "-avoid_negative_ts",
                    "make_zero",
                    str(output_path),
                ]
            )

            _run_ffmpeg(command, part_number)
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

        created.append(output_path)
        if progress_callback:
            progress_callback("part_completed", part_number, parts)

    return created
