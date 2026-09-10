import json
import subprocess
from pathlib import Path
from app.config import FFPROBE_BIN
from app.models.video import VideoInfo


def probe_video(path: Path) -> VideoInfo:
    command = [
        FFPROBE_BIN,
        "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,codec_name,width,height",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to analyze the video.")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    format_data = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    try:
        duration = float(format_data.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0.0

    if duration <= 0 or not video_stream:
        raise RuntimeError("The uploaded file does not contain a readable video stream.")

    return VideoInfo(
        filename=path.name,
        duration=duration,
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name"),
    )
