import pytest
from backend.app.models import Conversation

def test_export_pdf_not_found(client):
    response = client.get("/api/export/pdf/9999")
    assert response.status_code == 404

def test_export_pdf_success(client, setup_test_db):
    # First create a chat
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "llama3-70b-8192"
    })
    conv_id = response.json()["conversation_id"]

    # Then export
    export_response = client.get(f"/api/export/pdf/{conv_id}")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"] in ["application/pdf", "text/plain"]
    assert "attachment; filename=chat_" in export_response.headers["content-disposition"]

def test_export_txt_success(client, setup_test_db):
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "llama3-70b-8192"
    })
    conv_id = response.json()["conversation_id"]

    export_response = client.get(f"/api/export/txt/{conv_id}")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/plain")
