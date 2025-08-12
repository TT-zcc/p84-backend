# tests/test_auth_integration.py
import pytest
from research_assistant.app import create_app
from research_assistant.extensions import db
from research_assistant.user.models import User

@pytest.fixture
def app():
    """
    Create a fresh Flask app for each test with an in-memory SQLite database.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "PROPAGATE_EXCEPTIONS": True,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

# ---------- Helpers ----------
def register_via_api(client, username="testuser", email="test@example.com", password="123456"):
    resp = client.post("/users/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    return resp, resp.get_json()

def login_via_api(client, username, password):
    resp = client.post("/users/login", json={
        "username": username,
        "password": password,
    })
    return resp, resp.get_json()

# ---------- Registration ----------
def test_register_success_creates_user(client, app):
    """
    Happy case: Register a new user.
    Expect:
    - 200 OK
    - User persisted with hashed password
    """
    resp, data = register_via_api(client)
    assert resp.status_code == 200
    assert data["msg"] == "Registration successful"

    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        assert user is not None
        assert user.check_password("123456")  # password hashing verified

def test_register_missing_fields_is_400(client):
    resp = client.post("/users/register", json={"username": "onlyname"})
    assert resp.status_code == 400
    assert resp.get_json()["msg"] == "Missing fields"

def test_register_duplicate_username_is_400(client):
    register_via_api(client, username="dupuser", email="a@example.com")
    resp, data = register_via_api(client, username="dupuser", email="b@example.com")
    assert resp.status_code == 400
    assert data["msg"] == "Username already exists"

def test_register_duplicate_email_is_400(client):
    register_via_api(client, username="u1", email="same@example.com")
    resp, data = register_via_api(client, username="u2", email="same@example.com")
    assert resp.status_code == 400
    assert data["msg"] == "Email already exists"

# ---------- Login ----------
def test_login_success_returns_jwt(client):
    register_via_api(client, username="loginuser", email="login@example.com", password="pass123")
    resp, data = login_via_api(client, username="loginuser", password="pass123")
    assert resp.status_code == 200
    assert "access_token" in data
    assert isinstance(data["access_token"], str)

def test_login_invalid_password_is_401(client):
    register_via_api(client, username="who", email="who@example.com", password="rightpass")
    resp, data = login_via_api(client, username="who", password="wrongpass")
    assert resp.status_code == 401
    assert data["msg"] == "Invalid username or password"

def test_login_nonexistent_user_is_401(client):
    resp, data = login_via_api(client, username="ghost", password="whatever")
    assert resp.status_code == 401
    assert data["msg"] == "Invalid username or password"
