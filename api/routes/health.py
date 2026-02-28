"""Health check endpoint with system checks."""

import os
import time
from fastapi import APIRouter

router = APIRouter()

_start_time = time.time()


@router.get("/api/health")
async def health():
    checks = {}

    # Check required env vars
    required_vars = ["OPENAI_API_KEY"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    checks["env_vars"] = "ok" if not missing else f"missing: {', '.join(missing)}"

    # Check ChromaDB
    try:
        from vectordb.collections import get_chroma_client
        get_chroma_client()
        checks["chromadb"] = "ok"
    except Exception as e:
        checks["chromadb"] = f"error: {str(e)[:100]}"

    all_ok = all(v == "ok" for v in checks.values())
    uptime = round(time.time() - _start_time)

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "checks": checks,
    }
