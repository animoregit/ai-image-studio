"""
AI Image Studio — FastAPI application entry point.

Run with:
    uvicorn main:app --reload
    # or
    python main.py
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.storage import storage
from app.jobs import job_manager

from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.background import router as background_router
from app.api.upscale import router as upscale_router
from app.api.enhance import router as enhance_router
from app.api.editing import router as editing_router
from app.api.jobs import router as jobs_router
from app.api.batch import router as batch_router

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai_image_studio")


# ── App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Image Studio",
    description="Open-source AI image enhancement backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes (all under /api/v1) ──────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(health_router,    prefix=PREFIX)
app.include_router(upload_router,    prefix=PREFIX)
app.include_router(background_router, prefix=PREFIX)
app.include_router(upscale_router,   prefix=PREFIX)
app.include_router(enhance_router,   prefix=PREFIX)
app.include_router(editing_router,   prefix=PREFIX)
app.include_router(jobs_router,      prefix=PREFIX)
app.include_router(batch_router,     prefix=PREFIX)


# ── Lifecycle events ────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("Starting AI Image Studio backend on %s (device: %s)", settings.host, settings.device)
    logger.info("Upload dir : %s", settings.upload_dir)
    logger.info("Output dir : %s", settings.output_dir)
    logger.info("Models dir : %s", settings.models_dir)
    # Background cleanup loop
    asyncio.create_task(storage.start_cleanup_loop())
    asyncio.create_task(_job_cleanup_loop())


async def _job_cleanup_loop():
    """Periodically prune old completed jobs."""
    while True:
        try:
            removed = await job_manager.cleanup_old_jobs()
            if removed:
                logger.info("Pruned %d old jobs", removed)
        except Exception:
            logger.exception("Job cleanup failed")
        await asyncio.sleep(600)  # Every 10 minutes


# ── Direct run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
