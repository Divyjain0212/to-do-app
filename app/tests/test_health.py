import os

import pytest

from src.app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_NAME", "todo")
    monkeypatch.setenv("DB_USER", "todo")
    monkeypatch.setenv("DB_PASSWORD", "todo")

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_returns_json(client):
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert "status" in response.get_json()
