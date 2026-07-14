import pytest

def test_create_share(client, setup_test_db):
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "llama3-70b-8192"
    })
    conv_id = response.json()["conversation_id"]

    share_response = client.post("/api/share/", json={
        "conversation_id": conv_id,
        "is_public": True
    })
    assert share_response.status_code == 200
    data = share_response.json()
    assert "share_id" in data
    assert "share_url" in data

    share_id = data["share_id"]

    view_response = client.get(f"/api/share/{share_id}")
    assert view_response.status_code == 200
    view_data = view_response.json()
    assert view_data["share_id"] == share_id
    assert view_data["title"] == "Test Chat"
    assert "messages" in view_data
