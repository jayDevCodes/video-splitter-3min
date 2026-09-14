import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR
from app.routes.progress import router as progress_router
from app.routes.video import router as video_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Video Splitter 3 Min", version="2.0.0")
app.include_router(video_router)
app.include_router(progress_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
