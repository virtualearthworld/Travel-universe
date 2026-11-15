from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app import main


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def head_bucket(self, **kwargs):
        if not self.objects.get("bucket_exists"):
            raise ClientError({"Error": {"Code": "404", "Message": "Not found"}}, "HeadBucket")

    def create_bucket(self, **kwargs):
        self.objects["bucket_exists"] = True

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs=None):
        self.objects[key] = fileobj.read()

    def delete_object(self, Bucket, Key):
        self.deleted.append(Key)
        self.objects.pop(Key, None)


class FakeTask:
    id = "job-test-123"


def test_health_endpoint():
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_stores_video_and_queues_job(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr(main, "storage_client", lambda: storage)
    monkeypatch.setattr(main.celery, "send_task", lambda *args, **kwargs: FakeTask())

    response = TestClient(main.app).post(
        "/api/v1/videos/upload",
        files={"file": ("trip.mp4", b"fake-video-bytes", "video/mp4")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["job_id"] == "job-test-123"
    assert payload["video_id"]
    assert len([key for key in storage.objects if key.startswith("uploads/")]) == 1


def test_upload_rejects_unsupported_file():
    response = TestClient(main.app).post(
        "/api/v1/videos/upload",
        files={"file": ("notes.txt", b"not-a-video", "text/plain")},
    )
    assert response.status_code == 415


def test_bucket_permission_error_is_not_mistaken_for_missing_bucket():
    class ForbiddenStorage:
        def head_bucket(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "403", "Message": "Forbidden"}},
                "HeadBucket",
            )

        def create_bucket(self, **kwargs):
            raise AssertionError("Must not attempt bucket creation after a permission error")

    try:
        main.ensure_bucket(ForbiddenStorage())
        assert False, "Expected storage to be reported unavailable"
    except main.HTTPException as exc:
        assert exc.status_code == 503


def test_preprocessing_job_never_reports_world_ready(monkeypatch):
    class CompletedPreprocessing:
        state = "SUCCESS"
        result = {
            "status": "frames_extracted_gpu_stage_required",
            "reconstruction_inputs_key": "reconstruction-inputs/test/inputs.zip",
        }
        info = None

        def successful(self):
            return True

        def failed(self):
            return False

    monkeypatch.setattr(main.celery, "AsyncResult", lambda job_id: CompletedPreprocessing())
    response = TestClient(main.app).get("/api/v1/jobs/job-test-123")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["world_ready"] is False
