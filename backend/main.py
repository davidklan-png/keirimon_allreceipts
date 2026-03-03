"""
FastAPI application for AllReceipts.

Main entry point — registers all routes and middleware.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, get_engine
from .models import Receipt, Vendor, NtaCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes database on startup.
    """
    # Initialize database tables
    init_db()

    # TODO: Load seed vendors.json into Vendor table if empty
    # TODO: Start background tasks (NTA cache cleanup, etc.)

    yield

    # Cleanup on shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="AllReceipts API",
    description="Receipt capture and management for Japanese GK",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
def health_check():
    """Basic health check for monitoring."""
    return {"status": "ok"}


# Route registration
from .routes import receipts, ocr, search, export, audit, vendors

app.include_router(receipts.router, prefix="/api", tags=["receipts"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["ocr"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(vendors.router, prefix="/api/vendors", tags=["vendors"])


if __name__ == "__main__":
    import uvicorn

    # Default to port 8000, respect PORT env var if set
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
