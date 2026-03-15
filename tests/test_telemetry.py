"""Tests for the POST /api/telemetry endpoint."""

import json
import logging
import sys
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("langchain.schema", MagicMock())
sys.modules.setdefault("langchain_openai", MagicMock())

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


class TestTelemetryEndpoint:
    """Test frontend telemetry ingestion."""

    def test_valid_batch(self):
        payload = {
            "entries": [
                {"level": "info", "message": "page loaded"},
                {"level": "warn", "message": "slow render"},
                {"level": "error", "message": "api timeout"},
            ]
        }
        resp = client.post("/api/telemetry", json=payload)
        assert resp.status_code == 204

    def test_invalid_level_rejected(self):
        payload = {"entries": [{"level": "critical", "message": "boom"}]}
        resp = client.post("/api/telemetry", json=payload)
        assert resp.status_code == 422

    def test_empty_batch(self):
        resp = client.post("/api/telemetry", json={"entries": []})
        assert resp.status_code == 204

    def test_message_too_long_rejected(self):
        payload = {"entries": [{"level": "info", "message": "x" * 1001}]}
        resp = client.post("/api/telemetry", json=payload)
        assert resp.status_code == 422

    def test_batch_size_limit(self):
        entries = [{"level": "info", "message": f"msg {i}"} for i in range(21)]
        resp = client.post("/api/telemetry", json={"entries": entries})
        assert resp.status_code == 422

    def test_log_output(self, caplog):
        with caplog.at_level(logging.INFO, logger="jobaid.frontend"):
            payload = {
                "entries": [
                    {
                        "level": "error",
                        "message": "something broke",
                        "session_id": "abc-123",
                    }
                ]
            }
            client.post("/api/telemetry", json=payload)

        # Find the log record emitted by the telemetry handler
        frontend_records = [
            r for r in caplog.records if r.name == "jobaid.frontend"
        ]
        assert len(frontend_records) >= 1
        data = json.loads(frontend_records[-1].message)
        assert data["event"] == "frontend"
        assert data["message"] == "something broke"
        assert data["session_id"] == "abc-123"
