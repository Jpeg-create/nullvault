import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code in [201, 400]


def test_login():
    client.post("/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "testpassword123"
    })
    response = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_secrets_require_auth():
    response = client.get("/secrets/")
    assert response.status_code == 401


def test_audit_requires_auth():
    response = client.get("/audit/")
    assert response.status_code == 401
