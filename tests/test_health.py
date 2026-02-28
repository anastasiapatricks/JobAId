"""Health endpoint tests."""

import sys
import pytest
from unittest.mock import MagicMock

# Mock the heavy dependency chain before importing the app
sys.modules.setdefault("langchain.schema", MagicMock())
sys.modules.setdefault("langchain_openai", MagicMock())

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test /api/health endpoint."""

    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_status(self):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] in ("healthy", "degraded")

    def test_health_returns_version(self):
        response = client.get("/api/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.2.0"

    def test_health_returns_uptime(self):
        response = client.get("/api/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)

    def test_health_returns_checks(self):
        response = client.get("/api/health")
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)
