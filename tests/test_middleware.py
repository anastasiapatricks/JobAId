"""Tests for RequestLoggingMiddleware session_id extraction and query logging."""

import json
import logging
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("langchain.schema", MagicMock())
sys.modules.setdefault("langchain_openai", MagicMock())

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


class TestRequestLoggingMiddleware:
    """Test middleware structured log entries."""

    def test_session_id_extracted(self, caplog):
        fake_id = "00000000-0000-0000-0000-000000000001"
        with caplog.at_level(logging.INFO, logger="jobaid.api"):
            client.get(f"/api/sessions/{fake_id}")

        api_records = [r for r in caplog.records if r.name == "jobaid.api"]
        assert len(api_records) >= 1
        data = json.loads(api_records[-1].message)
        assert data["session_id"] == fake_id

    def test_no_session_id_for_health(self, caplog):
        with caplog.at_level(logging.INFO, logger="jobaid.api"):
            client.get("/api/health")

        api_records = [r for r in caplog.records if r.name == "jobaid.api"]
        assert len(api_records) >= 1
        data = json.loads(api_records[-1].message)
        assert "session_id" not in data

    def test_query_params_logged(self, caplog):
        with caplog.at_level(logging.INFO, logger="jobaid.api"):
            client.get("/api/health?foo=bar")

        api_records = [r for r in caplog.records if r.name == "jobaid.api"]
        assert len(api_records) >= 1
        data = json.loads(api_records[-1].message)
        assert data["query"] == "foo=bar"
