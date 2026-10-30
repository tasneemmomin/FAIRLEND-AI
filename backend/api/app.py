from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.core.config import settings
from backend.db.session import init_db
from backend.api.routes import health, intake, officer, websocket, documents, voice, explain, fairness, privacy, auth

def create_app() -> FastAPI:
    app = FastAPI(
        title="FairLendAI API",
        description="Real-Time, Explainable, Voice-Enabled AI Loan Assessment Platform",
        version=settings.VERSION,
    )

    # CORS configuration for development and local access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure tables are initialized on startup
    @app.on_event("startup")
    def on_startup():
        init_db()

    # Mount API endpoints
    app.include_router(auth.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(intake.router, prefix="/api")
    app.include_router(officer.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(voice.router, prefix="/api")
    app.include_router(explain.router, prefix="/api")
    app.include_router(fairness.router, prefix="/api")
    app.include_router(privacy.router, prefix="/api")
    app.include_router(websocket.router, prefix="/api")

    # Frontend single-port serving
    frontend_dist = settings.BASE_DIR / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Don't intercept API routes
            if full_path.startswith("api/") or full_path == "api":
                return {"error": "API route not found"}
            file_path = frontend_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    return app

app = create_app()
