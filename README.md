# Video Splitter 3 Min

A local FastAPI + FFmpeg application for splitting a video into sequential clips. **This project does not upload videos to YouTube, Facebook, Instagram, or any other platform.**

## What it does

- Upload one source video through the local web UI.
- Split the complete video into sequential parts.
- Default part length: **180 seconds (3 minutes)**.
- Choose a custom part length from 1–3600 seconds.
- Generate vertical 1080×1920 (9:16) clips.
- Generate horizontal 1920×1080 (16:9) clips.
- Generate vertical full-frame 1080×1920 clips without cropping; the source is centered on a black canvas with the existing Part N / Like and comment overlay.
- Preserve audio when available.
- Store each source video's parts in its own output folder.
- Use ordered filenames such as `part_001.mp4`, `part_002.mp4`, etc.
- Show generation progress in the local web UI.

## What was removed

All social-upload functionality has been removed from the application, including:

- YouTube upload APIs and OAuth.
- Facebook/Instagram upload integrations and OAuth.
- Multi-account management.
- Automatic upload watcher/queue.
- Upload gap scheduling and upload status tracking.
- Upload metadata and thumbnail management.
- Upload-related UI and account screens.
- Google API authentication dependencies.

The application now has one responsibility: **split the source video and save the generated clips locally.**

## Output

```text
output/
└── my_video_ab12cd34/
    ├── part_001.mp4
    ├── part_002.mp4
    ├── part_003.mp4
    └── READY
```

## Requirements

- Python 3.11+
- FFmpeg and FFprobe available on PATH, or configure their paths in `.env`.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Configuration

Copy `.env.example` to `.env` if you want to change defaults:

```env
CHUNK_SECONDS=180
MAX_UPLOAD_MB=5120
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

## API

### Start a background split job

`POST /api/video/split/start`

Multipart field:

- `file` — source video

Query parameters:

- `chunk_seconds` — 1 to 3600, default 180
- `orientation` — `vertical`, `horizontal`, or `vertical_full_frame`

### Synchronous split

`POST /api/video/split`

Uses the same file and query parameters and returns the generated part list when processing finishes.

### Job status

`GET /api/jobs/{job_id}`

### Live job events

`GET /api/jobs/{job_id}/events`

### Health

`GET /api/health`

## License

See [LICENSE](LICENSE).
