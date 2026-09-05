import pytest

def test_list_models(client):
    response = client.get("/api/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "default" in data

def test_chat_stream(client, monkeypatch):
    async def mock_stream(*args, **kwargs):
        yield "Hello "
        yield "world!"

    async def mock_title(*args, **kwargs):
        return "Chat Title"

    monkeypatch.setattr("backend.app.routes.chat.stream_chat", mock_stream)
    monkeypatch.setattr("backend.app.routes.chat.auto_title", mock_title)
    response = client.post("/api/chat/stream", json={
        "message": "Hello",
        "model": "openai/gpt-oss-120b"
    })
    assert response.status_code == 200
    assert "Hello" in response.text


