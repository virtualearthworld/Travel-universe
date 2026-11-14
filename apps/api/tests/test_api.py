from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_root_exposes_version():
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json()["name"] == "Travel Universe API"

def test_upload_rejects_unsupported_file_before_storage():
    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 415
    assert "MP4" in response.json()["detail"]

def test_upload_rejects_mismatched_content_type_before_storage():
    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("holiday.mp4", b"not a video", "text/plain")},
    )
    assert response.status_code == 415
