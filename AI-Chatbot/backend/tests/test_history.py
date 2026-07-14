import pytest

def test_new_chat(client):
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "llama3-70b-8192"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "conversation_id" in data

def test_history_root(client):
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "conversations" in data
