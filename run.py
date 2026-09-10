import uvicorn

from app.services.upload_watcher import UploadWatcher


if __name__ == "__main__":
    watcher = UploadWatcher()
    watcher.start()
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
    finally:
        watcher.stop()
