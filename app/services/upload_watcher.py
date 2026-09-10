from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from app.config import OUTPUT_DIR, UPLOAD_WATCH_INTERVAL
from app.services.metadata_manager import is_ready, load_metadata
from app.services.youtube_uploader import upload_pending_folder

logger = logging.getLogger(__name__)


class UploadWatcher:
    def __init__(self, interval: int = UPLOAD_WATCH_INTERVAL):
        self.interval = max(5, interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="youtube-upload-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception:
                logger.exception("YouTube upload watcher scan failed")
            self._stop.wait(self.interval)

    def scan_once(self) -> None:
        for output_dir in sorted(OUTPUT_DIR.iterdir()):
            if not output_dir.is_dir() or not is_ready(output_dir):
                continue
            try:
                metadata = load_metadata(output_dir)
                if metadata.get("upload", {}).get("auto_upload", False):
                    results = upload_pending_folder(output_dir)
                    if results:
                        logger.info("Processed %s: %s", output_dir.name, results)
            except Exception:
                logger.exception("Failed processing output folder %s", output_dir)
