from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import FRONTEND_DIR
from app.routes.video import router as video_router
from app.routes.youtube import router as youtube_router
from app.routes.upload import router as upload_router
from app.routes.accounts import router as accounts_router
from app.routes.progress import router as progress_router
from app.services.account_manager import ensure_legacy_youtube_account

app = FastAPI(title="Video Splitter 3 Min", version="1.4.0")

# Keep legacy single-account YouTube installations working without coupling
# account registry tests to production bootstrap behavior.
ensure_legacy_youtube_account()

app.include_router(video_router)
app.include_router(youtube_router)
app.include_router(upload_router)
app.include_router(accounts_router)
app.include_router(progress_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
