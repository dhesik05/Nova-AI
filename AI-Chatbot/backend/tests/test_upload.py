import pytest
from unittest.mock import patch

def test_upload_pdf(client, setup_test_db):
    response = client.post("/new-chat", data={
        "title": "Test Chat",
        "model": "openai/gpt-oss-120b"
    })
    conv_id = response.json()["conversation_id"]

    with patch("backend.app.routes.upload.process_pdf", return_value=5):
        response = client.post(
            "/api/upload/pdf",
            data={"conversation_id": conv_id},
            files={"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chunks"] == 5

def test_upload_pdf_auto_create(client, setup_test_db):
    with patch("backend.app.routes.upload.process_pdf", return_value=3):
        response = client.post(
            "/api/upload/pdf",
            files={"file": ("resume.pdf", b"sample resume content", "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversation_id" in data
        assert data["chunks"] == 3

def test_upload_image(client, setup_test_db):
    response = client.post(
        "/api/upload/image",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data_url" in data
    assert data["data_url"].startswith("data:image/png;base64,")

