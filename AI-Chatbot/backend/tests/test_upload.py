import pytest
from unittest.mock import patch

def test_upload_pdf(client, setup_test_db):
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "llama3-70b-8192"
    })
    conv_id = response.json()["conversation_id"]

    with patch("backend.app.routes.upload.process_pdf", return_value=5):
        # We need to send multipart/form-data
        response = client.post(
            "/api/upload/pdf",
            data={"conversation_id": conv_id},
            files={"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chunks"] == 5
