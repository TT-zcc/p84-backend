import io
import pytest
from unittest.mock import MagicMock

from research_assistant.extensions import db
from research_assistant.writing_tool.models import CloudDocument, DocumentVersion


# ===== Helpers =====

def _seed_doc_version(uploader_id: int):
    """Helper to create a document with a single version."""
    doc = CloudDocument(title="Test Doc")
    db.session.add(doc)
    db.session.flush()
    ver = DocumentVersion(
        document_id=doc.id,
        major_version=1,
        minor_version=0,
        file_key=f"documents/{doc.id}_v1.0_test.docx",
        file_url="s3://dummy/url",
        uploaded_by_id=uploader_id,
        file_size=0.12,
        is_current=True,
    )
    db.session.add(ver)
    db.session.commit()
    return doc


def _make_mock_s3_client():
    """Build a minimal mock S3 client used by routes."""
    m = MagicMock()
    m.generate_presigned_url.return_value = "https://mock-presigned-url"
    m.delete_object.return_value = None
    return m


# ===== Create Document Tests =====

def test_create_document_success(auth_client, test_user, monkeypatch):
    """Test creating a new document with first version."""
    # Patch routes-level reference to avoid real S3 upload
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )

    file_data = (io.BytesIO(b"file content"), "test.docx")
    res = auth_client.post(
        "/writing_tool/documents",
        data={"title": "My Doc", "file": file_data},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["code"] == 0
    assert "document_id" in json_data


@pytest.mark.parametrize(
    "data",
    [
        {"title": "Doc without file"},  # Missing file
        {},  # Missing title
    ],
)
def test_create_document_missing_fields(auth_client, data, monkeypatch):
    """Test creating a document with missing required fields returns 400."""
    # Patch routes-level reference defensively
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )

    res = auth_client.post(
        "/writing_tool/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1


# ===== List Documents Tests =====

def test_list_documents_returns_data(app, auth_client, test_user):
    """Test listing documents and their versions when data exists."""
    with app.app_context():
        doc = CloudDocument(title="Existing Doc")
        db.session.add(doc)
        db.session.flush()
        ver = DocumentVersion(
            document_id=doc.id,
            major_version=1,
            minor_version=0,
            file_key="mockkey",
            file_url="https://mock-url",
            uploaded_by_id=test_user.id,
            file_size=1.2,
            is_current=True,
        )
        db.session.add(ver)
        db.session.commit()

    res = auth_client.get("/writing_tool/documents")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data) >= 1
    assert data[0]["title"] == "Existing Doc"
    assert "versions" in data[0]


def test_list_documents_empty(auth_client):
    """Test listing documents returns empty list when no data exists."""
    res = auth_client.get("/writing_tool/documents")
    assert res.status_code == 200
    assert res.get_json().get("data") == []


# ===== Upload New Version Tests =====

def test_upload_new_version_minor_increment(app, auth_client, test_user, monkeypatch):
    """Upload a new version when v1.0 exists; should increment to v1.1, update is_current, and set uploaded_by_id."""
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )

    with app.app_context():
        doc = CloudDocument(title="Doc A")
        db.session.add(doc)
        db.session.flush()
        v10 = DocumentVersion(
            document_id=doc.id, major_version=1, minor_version=0,
            file_key=f"documents/{doc.id}_v1.0_a.docx",
            file_url="s3://dummy/a",
            uploaded_by_id=test_user.id, file_size=0.5, is_current=True,
        )
        db.session.add(v10)
        db.session.commit()
        doc_id = doc.id

    file_data = (io.BytesIO(b"new content"), "a.docx")
    res = auth_client.post(
        f"/writing_tool/documents/{doc_id}/versions",
        data={"file": file_data},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["code"] == 0
    assert json_data["version"] == "v1.1"


def test_upload_new_version_rollover(app, auth_client, test_user, monkeypatch):
    """Upload new version when v1.9 exists; should roll over to v2.0."""
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )
    with app.app_context():
        doc = CloudDocument(title="Doc B")
        db.session.add(doc)
        db.session.flush()
        v19 = DocumentVersion(
            document_id=doc.id, major_version=1, minor_version=9,
            file_key=f"documents/{doc.id}_v1.9_b.docx",
            file_url="s3://dummy/b",
            uploaded_by_id=test_user.id, file_size=0.5, is_current=True,
        )
        db.session.add(v19)
        db.session.commit()
        doc_id = doc.id

    file_data = (io.BytesIO(b"new content"), "b.docx")
    res = auth_client.post(
        f"/writing_tool/documents/{doc_id}/versions",
        data={"file": file_data},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    assert res.get_json()["version"] == "v2.0"


def test_upload_new_version_missing_file(auth_client, test_user):
    """Uploading a new version without a file should return 400."""
    res = auth_client.post(
        "/writing_tool/documents/1/versions",
        data={},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1
    assert "Missing file" in res.get_json()["msg"]


def test_upload_new_version_document_not_found(auth_client, monkeypatch):
    """Uploading a new version for a non-existent document should return 404."""
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )
    file_data = (io.BytesIO(b"new content"), "a.docx")
    res = auth_client.post(
        "/writing_tool/documents/999/versions",
        data={"file": file_data},
        content_type="multipart/form-data",
    )
    assert res.status_code == 404

def test_upload_new_version_first_time(app, auth_client, test_user, monkeypatch):
    """Upload a version when the document has no previous versions; should start at v1.0."""
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.upload_file_to_s3",
        lambda f, k: f"https://mock-s3/{k}",
        raising=True,
    )

    with app.app_context():
        # Create document without versions
        doc = CloudDocument(title="Empty Doc")
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    file_data = (io.BytesIO(b"first content"), "first.docx")
    res = auth_client.post(
        f"/writing_tool/documents/{doc_id}/versions",
        data={"file": file_data},
        content_type="multipart/form-data",
    )

    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["code"] == 0
    assert json_data["version"] == "v1.0"

# ===== Download Version Tests =====

def test_download_version_success(app, auth_client, test_user, monkeypatch):
    """Test successfully generating a download link for an existing document version."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    res = auth_client.get(f"/writing_tool/documents/{doc_id}/versions/v1.0/download")
    assert res.status_code == 200
    assert res.get_json()["file_url"].startswith("https://mock-presigned-url")


def test_download_version_invalid_format(auth_client):
    """Test that downloading a version with an invalid version_id format returns 400."""
    resp = auth_client.get("/writing_tool/documents/1/versions/invalid-format/download")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1
    assert "Invalid version_id format" in resp.get_json()["msg"]


def test_download_version_unauthorized(app, auth_client, test_user, monkeypatch):
    """Downloading a version uploaded by another user should return 403."""
    with app.app_context():
        other_user_id = test_user.id + 1
        doc = _seed_doc_version(uploader_id=other_user_id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )
    res = auth_client.get(f"/writing_tool/documents/{doc_id}/versions/v1.0/download")
    assert res.status_code == 403
    assert res.get_json()["code"] == 1


def test_download_version_s3_exception(app, auth_client, test_user, monkeypatch):
    """Test that an S3 error during download link generation returns 500."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    mock_client.generate_presigned_url.side_effect = Exception("boom")
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    resp = auth_client.get(f"/writing_tool/documents/{doc_id}/versions/v1.0/download")
    assert resp.status_code == 500
    assert resp.get_json()["code"] == 1
    assert "Failed to generate download link" in resp.get_json()["msg"]


# ===== Delete Version Tests =====

def test_delete_version_success(app, auth_client, test_user, monkeypatch):
    """Test deleting a specific document version successfully."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    res = auth_client.delete(f"/writing_tool/documents/{doc_id}/versions/v1.0")
    assert res.status_code == 200
    assert res.get_json()["code"] == 0


def test_delete_version_invalid_format(auth_client):
    """Test that deleting a version with an invalid version_id format returns 400."""
    resp = auth_client.delete("/writing_tool/documents/1/versions/not-a-version")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1
    assert "Invalid version_id format" in resp.get_json()["msg"]


def test_delete_version_s3_exception(app, auth_client, test_user, monkeypatch):
    """Test that an S3 error during version deletion returns 500."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    mock_client.delete_object.side_effect = Exception("delete fail")
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    resp = auth_client.delete(f"/writing_tool/documents/{doc_id}/versions/v1.0")
    assert resp.status_code == 500
    assert resp.get_json()["code"] == 1
    assert "Failed to delete file from S3" in resp.get_json()["msg"]


# ===== Delete Document Tests =====

def test_delete_document_success(app, auth_client, test_user, monkeypatch):
    """Test deleting a document and all its versions successfully."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    resp = auth_client.delete(f"/writing_tool/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_delete_document_s3_exception(app, auth_client, test_user, monkeypatch):
    """Test that an S3 error during document deletion returns 500."""
    with app.app_context():
        doc = _seed_doc_version(uploader_id=test_user.id)
        doc_id = doc.id

    mock_client = _make_mock_s3_client()
    mock_client.delete_object.side_effect = Exception("bulk delete fail")
    monkeypatch.setattr(
        "research_assistant.writing_tool.routes.get_s3_client",
        lambda: mock_client,
        raising=True,
    )

    resp = auth_client.delete(f"/writing_tool/documents/{doc_id}")
    assert resp.status_code == 500
    assert resp.get_json()["code"] == 1
    assert "Failed to delete file" in resp.get_json()["msg"]
