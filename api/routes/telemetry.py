"""Frontend telemetry ingestion endpoint."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["telemetry"])
logger = logging.getLogger("jobaid.frontend")


class FrontendLogEntry(BaseModel):
    level: str = Field(pattern=r"^(info|warn|error)$")
    message: str = Field(max_length=1000)
    context: Optional[dict] = None
    timestamp: Optional[str] = None
    session_id: Optional[str] = None


class TelemetryBatch(BaseModel):
    entries: List[FrontendLogEntry] = Field(max_length=20)


@router.post("/telemetry", status_code=204)
async def ingest_telemetry(batch: TelemetryBatch):
    for entry in batch.entries:
        log_data = {
            "event": "frontend",
            "message": entry.message,
        }
        if entry.session_id:
            log_data["session_id"] = entry.session_id
        if entry.timestamp:
            log_data["client_ts"] = entry.timestamp
        if entry.context:
            log_data["context"] = entry.context

        log_line = json.dumps(log_data)
        if entry.level == "error":
            logger.error(log_line)
        elif entry.level == "warn":
            logger.warning(log_line)
        else:
            logger.info(log_line)
