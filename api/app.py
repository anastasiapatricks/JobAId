"""FastAPI application factory for JobAId."""

import sys
import os
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

# Configure structured logging for jobaid loggers (LLM calls, API requests)
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
logging.getLogger("jobaid").setLevel(logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.middleware import RequestLoggingMiddleware
from api.routes import health, sessions, pipeline, resume


def create_app() -> FastAPI:
    app = FastAPI(
        title="JobAId API",
        description="LLM-powered multi-agent job search assistant",
        version="0.2.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Seed ChromaDB on startup
    @app.on_event("startup")
    async def startup():
        try:
            from vectordb.seed_data import seed_all
            seed_all()
        except Exception as exc:
            import logging
            logging.getLogger("jobaid.api").warning(f"ChromaDB seeding failed: {exc}")

    # Routes
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(pipeline.router)
    app.include_router(resume.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
