# Video Splitter 3 Min

A local FastAPI + FFmpeg tool that uploads one video and splits the complete video into sequential clips. By default, every clip is **180 seconds (3 minutes)** and the final clip can be shorter.

## Features

- Upload one video through a simple web UI.
- Split the complete source video into sequential parts.
- Default chunk length: 180 seconds.
- Custom chunk length is supported from the UI/API.
- Output names are ordered: `part_001.mp4`, `part_002.mp4`, etc.
- Each upload gets its own output folder under `output/`.
- Uses accurate FFmpeg cuts by re-encoding to avoid keyframe-boundary drift.
- No cloud upload or third-party storage required.

## Requirements

- Python 3.11+ recommended.
- FFmpeg and FFprobe installed and available on PATH.

### macOS

```bash
brew install ffmpeg
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install ffmpeg
```

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000`.

## Output example

For an 8:25 video:

```text
output/
└── my_video_ab12cd34/
    ├── part_001.mp4   # 0:00 - 3:00
    ├── part_002.mp4   # 3:00 - 6:00
    └── part_003.mp4   # 6:00 - 8:25
```

## API

`POST /api/video/split?chunk_seconds=180` with multipart field `file`.

Health check: `GET /api/health`.

## Configuration

Environment variables:

- `CHUNK_SECONDS` — default split length (default `180`).
- `MAX_UPLOAD_MB` — maximum uploaded file size (default `5120`).
- `FFMPEG_BIN` — FFmpeg executable name/path (default `ffmpeg`).
- `FFPROBE_BIN` — FFprobe executable name/path (default `ffprobe`).

## Notes

The app intentionally keeps generated videos out of Git via `.gitignore`. The repository stores source code only.
