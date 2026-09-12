import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import FRONTEND_DIR, managed_facebook_configured, missing_meta_oauth_config
from app.routes.video import router as video_router
from app.routes.youtube import router as youtube_router
from app.routes.upload import router as upload_router
from app.routes.accounts import router as accounts_router
from app.routes.oauth import router as oauth_router
from app.services.account_manager import ensure_legacy_youtube_account

logger = logging.getLogger(__name__)

ensure_legacy_youtube_account()

if managed_facebook_configured():
    logger.info("Managed Facebook connection: configured.")
else:
    logger.info("Managed Facebook connection: not configured. Add UPLOAD_POST_API_KEY to .env to enable it.")

missing_meta = missing_meta_oauth_config()
if missing_meta:
    logger.info("Direct Meta OAuth: optional/not configured. Missing: %s", ", ".join(missing_meta))
else:
    logger.info("Direct Meta OAuth: configured as an optional fallback.")

app = FastAPI(title="Video Splitter 3 Min", version="1.5.0")
app.include_router(video_router)
app.include_router(youtube_router)
app.include_router(upload_router)
app.include_router(accounts_router)
app.include_router(oauth_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
