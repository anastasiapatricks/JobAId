"""Session management lifecycle tests."""

import sys
import pytest
from unittest.mock import MagicMock

# Mock the heavy dependency chain before importing the app
sys.modules.setdefault("langchain.schema", MagicMock())
sys.modules.setdefault("langchain_openai", MagicMock())

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


class TestSessionLifecycle:
    """Test session create/get/delete lifecycle."""

    def test_create_session(self):
        response = client.post("/api/sessions", json={})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "created"

    def test_create_session_with_data(self):
        response = client.post(
            "/api/sessions",
            json={
                "resume_text": "Sample resume",
                "job_query": "software engineer",
                "location_preference": "Singapore",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"

    def test_get_session(self):
        # Create
        create_resp = client.post("/api/sessions", json={})
        session_id = create_resp.json()["session_id"]

        # Get
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["session_id"] == session_id

    def test_get_nonexistent_session(self):
        response = client.get("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_delete_session(self):
        # Create
        create_resp = client.post("/api/sessions", json={})
        session_id = create_resp.json()["session_id"]

        # Delete
        del_resp = client.delete(f"/api/sessions/{session_id}")
        assert del_resp.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_session(self):
        response = client.delete("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_list_sessions(self):
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
