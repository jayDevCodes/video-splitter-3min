from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import FRONTEND_DIR
from app.routes.video import router as video_router
from app.routes.youtube import router as youtube_router

app = FastAPI(title="Video Splitter 3 Min", version="1.1.0")
app.include_router(video_router)
app.include_router(youtube_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
