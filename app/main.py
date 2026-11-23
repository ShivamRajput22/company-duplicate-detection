from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from app.config import settings
from app.routers import health, imports, reviews, verification

app = FastAPI(
    title="Hybrid Intelligent Company Duplicate Detection System",
    description="Deterministic & Explainable Company Entity Matching System (Groups 1–8)",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(verification.router, prefix="/api")

# Mount frontend build if it exists
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "name": "Company Duplicate Detection API",
            "version": "1.0.0",
            "docs_url": "/docs",
            "health_url": "/api/health",
            "stats_url": "/api/database/stats"
        }
