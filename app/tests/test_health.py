import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from app/ (one level above this tests/ directory)
load_dotenv(Path(__file__).parent.parent / ".env")

import pytest
from src.app import create_app

@pytest.fixture
def client():

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client

def test_health_endpoint_returns_json(client):
    """Health endpoint always returns a JSON response."""
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert response.get_json() is not None


def test_health_content_type_is_json(client):
    """Health endpoint sets Content-Type to application/json."""
    response = client.get("/health")
    assert response.content_type.startswith("application/json")


def test_health_response_has_status_key(client):
    """Health endpoint JSON body contains a 'status' key."""
    response = client.get("/health")
    data = response.get_json()
    assert "status" in data


def test_health_status_value_is_string(client):
    """'status' value is a non-empty string."""
    response = client.get("/health")
    data = response.get_json()
    assert isinstance(data["status"], str)
    assert len(data["status"]) > 0


def test_health_status_value_is_valid(client):
    """'status' is either 'ok' (DB reachable) or 'degraded' (DB unreachable)."""
    response = client.get("/health")
    data = response.get_json()
    assert data["status"] in ("ok", "degraded")