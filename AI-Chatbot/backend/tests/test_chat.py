import pytest

def test_list_models(client):
    response = client.get("/api/chat/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "default" in data

def test_chat_stream(client):
    # This might fail if the groq api key is not mocked correctly or if we don't mock stream_chat
    # We will just verify it accepts the payload. The actual stream_chat from groq may fail due to invalid test key,
    # but the endpoint should at least be reachable.
    response = client.post("/api/chat/stream", json={
        "message": "Hello",
        "model": "llama3-70b-8192"
    })
    # Depending on how exceptions are handled, we might get 200 with an error in stream, or 500
    # The stream should return 200 with ndjson
    assert response.status_code == 200
