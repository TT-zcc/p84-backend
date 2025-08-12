# tests/unit/user_setting/test_user_setting.py
import pytest
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.user_settings.models import UserSettings


def _ensure_settings_user_id(app):
    """Create or get the dedicated settings test user and return its integer id."""
    with app.app_context():
        u = User.query.filter_by(email="settings_test@example.com").first()
        if not u:
            u = User(username="settings_user", email="settings_test@example.com")
            u.password = "OldPass1"  # mixed case for password tests
            u.active = True
            _db.session.add(u)
            _db.session.commit()
        return u.id


# ---------- 适配器 fixtures：不改 conftest.py 的前提下补上老名字 ----------
@pytest.fixture
def test_user_id(app):
    return _ensure_settings_user_id(app)

@pytest.fixture
def auth_header(auth_header_app, test_user_id):
    # 复用 conftest.py 里的 auth_header_app 工厂生成 Authorization 头
    return auth_header_app(test_user_id)
# --------------------------------------------------------------------


def test_get_settings_creates_defaults(client, app, test_user_id, auth_header):
    """
    If no settings row exists, GET /settings/ should create defaults
    and return them together with username/email.
    """
    with app.app_context():
        UserSettings.query.filter_by(user_id=test_user_id).delete()
        _db.session.commit()

    resp = client.get("/settings/", headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()

    # Profile echoes
    assert data["username"] == "settings_user"
    assert data["email"] == "settings_test@example.com"

    # Model defaults
    assert data["language"] == "en"
    assert data["theme"] == "light"
    assert data["notifications_enabled"] is True
    assert data["export_format"] == "pdf"


def test_update_settings(client, auth_header, app, test_user_id):
    """
    PUT /settings/ should update general settings and return new values.
    """
    payload = {
        "language": "zh",
        "theme": "dark",
        "notifications_enabled": False,
        "export_format": "docx",
    }
    resp = client.put("/settings/", json=payload, headers=auth_header)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "Settings updated"

    s = body["settings"]
    assert s["language"] == "zh"
    assert s["theme"] == "dark"
    assert s["notifications_enabled"] is False
    assert s["export_format"] == "docx"

    with app.app_context():
        row = UserSettings.query.filter_by(user_id=test_user_id).first()
        assert row is not None
        assert row.language == "zh"
        assert row.theme == "dark"
        assert row.notifications_enabled is False
        assert row.export_format == "docx"


def test_update_profile_success(client, auth_header, app, test_user_id):
    """
    PUT /settings/profile should update username and email.
    """
    new_username = "settings_user_renamed"
    new_email = "settings_user_renamed@example.com"

    resp = client.put(
        "/settings/profile",
        json={"username": new_username, "email": new_email},
        headers=auth_header,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["message"] == "Profile updated"
    assert data["username"] == new_username
    assert data["email"] == new_email

    with app.app_context():
        fresh = _db.session.get(User, test_user_id)
        assert fresh.username == new_username
        assert fresh.email == new_email


def test_change_password_validations_and_success(client, auth_header, app, test_user_id):
    """
    POST /settings/change-password should:
      - 401 on wrong current password
      - 400 on weak new password
      - 200 on valid change; DB hash should verify
    """
    # Wrong current password
    r_wrong = client.post(
        "/settings/change-password",
        json={"current_password": "TotallyWrong", "new_password": "NewPass1"},
        headers=auth_header,
    )
    assert r_wrong.status_code == 401
    assert "incorrect" in r_wrong.get_json()["error"].lower()

    # Weak new password
    r_weak = client.post(
        "/settings/change-password",
        json={"current_password": "OldPass1", "new_password": "weakpass"},
        headers=auth_header,
    )
    assert r_weak.status_code == 400
    assert "password must be at least 6 characters" in r_weak.get_json()["error"].lower()

    # Valid change
    r_ok = client.post(
        "/settings/change-password",
        json={"current_password": "OldPass1", "new_password": "NewPass1"},
        headers=auth_header,
    )
    assert r_ok.status_code == 200
    assert r_ok.get_json()["message"] == "Password updated successfully"

    # Verify in DB
    with app.app_context():
        fresh = _db.session.get(User, test_user_id)
        assert fresh.check_password("NewPass1") is True
        assert fresh.check_password("OldPass1") is False
