import pytest
from backend.app.models import User

def test_read_users_me(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"

def test_name_login(client, setup_test_db):
    response = client.post("/api/auth/login", json={"name": "Dhesik"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["name"] == "Dhesik"

def test_guest_auth(client, setup_test_db):
    response = client.post("/api/auth/guest")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["name"] == "Guest User"

