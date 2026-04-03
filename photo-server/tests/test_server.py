"""Unit tests for the photo server Flask app."""
import io
import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Set required env vars before importing the app
os.environ.setdefault("GCS_PHOTOS_BUCKET", "test-bucket")
os.environ.setdefault("UPLOAD_TOKEN", "test-token")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402


@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def mock_gcs(monkeypatch):
    """Patch GCS client so no real GCP calls are made."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = []
    monkeypatch.setattr(server, "_client", mock_client)
    return mock_client, mock_bucket


def _make_jpeg() -> bytes:
    img = Image.new("RGB", (10, 10), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ─── /health ──────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert b"ok" in r.data


# ─── /manage ──────────────────────────────────────────────────────────────────

def test_manage_no_token(client):
    r = client.get("/manage")
    assert r.status_code == 401


def test_manage_bad_token(client):
    r = client.get("/manage?token=wrong")
    assert r.status_code == 401


def test_manage_ok(client):
    r = client.get("/manage?token=test-token")
    assert r.status_code == 200
    assert b"Camper Hub Photos" in r.data


# ─── /upload ──────────────────────────────────────────────────────────────────

def test_upload_no_token(client):
    r = client.post("/upload")
    assert r.status_code == 401


def test_upload_no_file(client):
    r = client.post("/upload?token=test-token", data={})
    assert r.status_code == 400


def test_upload_ok(client, mock_gcs):
    _, mock_bucket = mock_gcs
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    data = {"photo": (io.BytesIO(_make_jpeg()), "test.jpg")}
    r = client.post(
        "/upload?token=test-token",
        data=data,
        content_type="multipart/form-data",
    )
    assert r.status_code == 201
    assert r.get_json()["ok"] is True
    mock_blob.upload_from_file.assert_called_once()


# ─── /photo/<filename> GET ────────────────────────────────────────────────────

def test_serve_photo_not_found(client, mock_gcs):
    _, mock_bucket = mock_gcs
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    mock_bucket.blob.return_value = mock_blob

    r = client.get("/photo/missing.jpg")
    assert r.status_code == 404


def test_serve_photo_ok(client, mock_gcs):
    _, mock_bucket = mock_gcs
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_bytes.return_value = _make_jpeg()
    mock_bucket.blob.return_value = mock_blob

    r = client.get("/photo/abc123.jpg")
    assert r.status_code == 200
    assert r.content_type == "image/jpeg"


# ─── /photo/<filename> DELETE ─────────────────────────────────────────────────

def test_delete_photo_no_token(client):
    r = client.delete("/photo/abc123.jpg")
    assert r.status_code == 401


def test_delete_photo_not_found(client, mock_gcs):
    _, mock_bucket = mock_gcs
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    mock_bucket.blob.return_value = mock_blob

    r = client.delete("/photo/missing.jpg?token=test-token")
    assert r.status_code == 404


def test_delete_photo_ok(client, mock_gcs):
    _, mock_bucket = mock_gcs
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_bucket.blob.return_value = mock_blob

    r = client.delete("/photo/abc123.jpg?token=test-token")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    mock_blob.delete.assert_called_once()


# ─── /qr.png ──────────────────────────────────────────────────────────────────

def test_qr_code(client):
    r = client.get("/qr.png?token=test-token")
    assert r.status_code == 200
    assert r.content_type == "image/png"
