"""Tests for public health and root endpoints."""


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Happin" in data["message"]
    assert "health" in data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_v1_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
