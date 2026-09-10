# Video Splitter 3 Min

A local FastAPI + FFmpeg tool that uploads one video, splits the complete video into sequential clips, converts clips to YouTube-friendly sizes, and can automatically upload Shorts to YouTube using the YouTube Data API.

## Features

- Upload one video through the web UI.
- Split the complete source video into sequential parts.
- Default chunk length: 180 seconds (3 minutes).
- Custom chunk length is supported.
- **Vertical output:** `1080 × 1920` (9:16), suitable for YouTube Shorts.
- **Horizontal output:** `1920 × 1080` (16:9).
- Resizing preserves aspect ratio; excess area is cropped instead of stretching.
- Ordered output names: `part_001.mp4`, `part_002.mp4`, etc.
- Every source video gets its own output folder.
- Every output folder contains one metadata configuration shared by all its Shorts.
- Optional common thumbnail for every Short in that folder.
- Background watcher automatically uploads folders configured with `auto_upload: true`.
- Upload state is saved per clip so already-uploaded clips are skipped after restart.
- OAuth credentials/tokens are ignored by Git and never need to be committed.

## Output architecture

```text
output/
└── my_video_ab12cd34/
    ├── _config/
    │   ├── metadata.json
    │   └── upload_status.json
    ├── thumbnail.jpg              # optional, shared by all Shorts
    ├── part_001.mp4
    ├── part_002.mp4
    ├── part_003.mp4
    └── READY                       # created only after splitting finishes
```

Example `metadata.json`:

```json
{
  "title_template": "Jungle Book | Mowgli Adventure #{number}",
  "description": "Watch this Short...\n\n#shorts #mowgli #junglestory",
  "tags": ["shorts", "mowgli", "jungle book"],
  "thumbnail": "thumbnail.jpg",
  "youtube": {
    "privacy": "private",
    "category_id": "22",
    "made_for_kids": false
  },
  "upload": {
    "enabled": true,
    "auto_upload": true
  }
}
```

Supported title variables:

- `{number}` → `1`, `2`, `3`...
- `{filename}` → the generated output-folder name

For example, `part_001.mp4` becomes `Jungle Book | Mowgli Adventure #1`.

## YouTube API setup

1. Create a Google Cloud project.
2. Enable **YouTube Data API v3**.
3. Configure the OAuth consent screen.
4. Create an OAuth **Desktop app** client.
5. Download the client JSON and save it locally as:

```text
credentials/client_secret.json
```

Do **not** commit that file. The app stores the OAuth token locally at:

```text
tokens/token.json
```

On the first automatic upload, the app opens a browser for Google authorization. Later runs reuse the saved token when possible.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000`.

The upload watcher starts automatically with `run.py` and checks the `output/` directory periodically.

## API

`POST /api/video/split?chunk_seconds=180&orientation=vertical` with multipart field `file`.

Additional form fields:

- `title_template` — common title pattern for all clips.
- `description` — common description.
- `tags` — comma-separated tags.
- `privacy` — `private`, `unlisted`, or `public`.
- `category_id` — YouTube category ID, default `22`.
- `made_for_kids` — `true`/`false` according to the actual content.
- `auto_upload` — `true` to enable automatic upload.
- `thumbnail` — optional JPG/JPEG/PNG shared by all clips.

## Configuration

Environment variables:

- `CHUNK_SECONDS` — default split length (`180`).
- `MAX_UPLOAD_MB` — maximum uploaded file size (`5120`).
- `FFMPEG_BIN` — FFmpeg executable/path (`ffmpeg`).
- `FFPROBE_BIN` — FFprobe executable/path (`ffprobe`).
- `UPLOAD_WATCH_INTERVAL` — watcher interval in seconds (`15`).

## Notes

Generated videos, OAuth credentials, and OAuth tokens are kept out of Git via `.gitignore`. The repository stores source code and configuration templates only.
