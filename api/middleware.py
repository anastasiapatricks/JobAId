"""Request logging middleware with structured JSON output."""

import json
import re
import time
import uuid
import logging
import contextvars
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("jobaid.api")

# Context vars — available to all downstream code for log correlation
current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_session_id", default=None
)
current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_request_id", default=None
)

_SESSION_RE = re.compile(r"/api/sessions/([0-9a-f-]{36})")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Attach request_id to request state for downstream use
        request.state.request_id = request_id

        # Set both context vars for downstream log correlation
        current_request_id.set(request_id)

        # Extract session_id from URL path and set in contextvars
        session_id = None
        match = _SESSION_RE.search(request.url.path)
        if match:
            session_id = match.group(1)
            current_session_id.set(session_id)

        response = await call_next(request)
        duration = round(time.time() - start, 3)

        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration": duration,
        }

        if session_id:
            log_entry["session_id"] = session_id

        query = str(request.url.query)
        if query:
            log_entry["query"] = query

        if response.status_code >= 400:
            logger.warning(json.dumps(log_entry))
        else:
            logger.info(json.dumps(log_entry))

        return response
