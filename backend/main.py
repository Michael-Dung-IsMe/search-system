"""FastAPI Application Entrypoint for Multimodal Shopping Search Engine.

Configures CORS, Global Exception Handlers, Static Image Mounts, and Search Routes.
"""

from __future__ import annotations

# Hot reload trigger for environment and database configuration

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.routes.search_routes import router as search_router
from backend.schemas.api import ErrorResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api_main")

app = FastAPI(
    title="Interactive Multimodal Shopping Search Engine API",
    description="Backend API for object-aware multimodal search and explainable reranking.",
    version="1.0.0",
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Next.js dev server on localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Global Exception Handlers (Strict No-Silent-Failures standard)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats all standard HTTPExceptions into structured ErrorResponse."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_type="HTTPException",
            message=str(exc.detail),
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catches unexpected exceptions with detailed error context."""
    logger.error("Unhandled server exception at %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_type=type(exc).__name__,
            message="Internal Server Error occurred during request processing.",
            detail=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(),
    )


# 3. Mount Static Product & Upload Images
data_images_dir = Path(os.getenv("DATA_IMAGES_DIR", "data/images"))
data_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(data_images_dir)), name="images")

data_uploads_dir = Path("data/uploads")
data_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(data_uploads_dir)), name="uploads")


# 4. Health Check Endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """System liveness check."""
    return {"status": "ok", "service": "Interactive Multimodal Shopping Search API"}


# 5. Include Search Routes
app.include_router(search_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
