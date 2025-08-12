import pytest
from research_assistant.app import create_app
from research_assistant.extensions import db
from research_assistant.user.models import User

@pytest.fixture
def app():
    """
    Create and configure a new app instance for each test.
    Uses SQLite in-memory database for isolation.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """
    Flask test client for sending HTTP requests to the app.
    """
    return app.test_client()

@pytest.fixture
def create_user(app):
    """
    Helper fixture to create a test user in the database.
    Password is hashed using the model's password setter.
    """
    def _create(username="testuser", email="test@example.com", password="123456"):
        user = User(username=username, email=email)
        user.password = password
        db.session.add(user)
        db.session.commit()
        return user
    return _create

def test_login_success(client, create_user):
    """
    Happy case:
    - Existing user
    - Correct password
    Expect:
    - 200 OK
    - JSON response containing access_token
    """
    create_user()
    resp = client.post("/users/login", json={
        "username": "testuser",
        "password": "123456"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)

def test_login_invalid_password(client, create_user):
    """
    Sad case:
    - Existing user
    - Incorrect password
    Expect:
    - 401 Unauthorized
    - JSON message indicating invalid credentials
    """
    create_user()
    resp = client.post("/users/login", json={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert resp.status_code == 401
    assert resp.get_json()["msg"] == "Invalid username or password"

def test_login_nonexistent_user(client):
    """
    Sad case:
    - Username does not exist in the database
    Expect:
    - 401 Unauthorized
    - JSON message indicating invalid credentials
    """
    resp = client.post("/users/login", json={
        "username": "no_such_user",
        "password": "123456"
    })
    assert resp.status_code == 401
    assert resp.get_json()["msg"] == "Invalid username or password"
