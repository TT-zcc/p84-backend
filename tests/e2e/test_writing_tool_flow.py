import io
import pytest
import requests

BASE_URL = "http://flask-prod:5000"

@pytest.fixture
def register_and_login():
    session = requests.Session()
    username = "e2e_user"
    email = "e2e@example.com"
    password = "123456"

    # Try to register (ignore if already exists)
    session.post(f"{BASE_URL}/users/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    res = session.post(f"{BASE_URL}/users/login", json={
        "username": username,
        "password": password
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    return {"session": session, "token": token}

def test_full_writing_tool_flow(register_and_login):
    session = register_and_login["session"]
    token = register_and_login["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a new document
    files = {
        "file": ("doc1.docx", io.BytesIO(b"first version content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }
    res = session.post(
        f"{BASE_URL}/writing_tool/documents",
        headers=headers,
        files=files,
        data={"title": "E2E Document"}
    )
    assert res.status_code == 200, f"Document creation failed: {res.text}"
    document_id = res.json()["document_id"]

    # 2. Upload a new version
    files_v2 = {
        "file": ("doc1_v2.docx", io.BytesIO(b"second version"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }
    res = session.post(
        f"{BASE_URL}/writing_tool/documents/{document_id}/versions",
        headers=headers,
        files=files_v2
    )
    assert res.status_code == 200, f"Version upload failed: {res.text}"
    version_str = res.json()["version"]

    # 3. Download version
    res = session.get(
        f"{BASE_URL}/writing_tool/documents/{document_id}/versions/{version_str}/download",
        headers=headers
    )
    assert res.status_code == 200, f"Download failed: {res.text}"
    assert "file_url" in res.json()

    # 4. Delete version
    res = session.delete(
        f"{BASE_URL}/writing_tool/documents/{document_id}/versions/{version_str}",
        headers=headers
    )
    assert res.status_code == 200, f"Delete version failed: {res.text}"
    assert res.json()["code"] == 0

    # 5. Delete entire document
    res = session.delete(
        f"{BASE_URL}/writing_tool/documents/{document_id}",
        headers=headers
    )
    assert res.status_code == 200, f"Delete document failed: {res.text}"
    assert res.json()["code"] == 0
