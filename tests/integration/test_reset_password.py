# tests/integration/test_reset_password.py
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from research_assistant.app import create_app
from research_assistant.extensions import db
from research_assistant.user.models import User, EmailCaptcha


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        WTF_CSRF_ENABLED=False,
        PROPAGATE_EXCEPTIONS=True,
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_and_captcha(app):
    with app.app_context():
        email = f"alice+{uuid.uuid4().hex[:6]}@example.com"
        username = f"alice_{uuid.uuid4().hex[:6]}"

        u = User(username=username, email=email)
        u.password = "old_password"
        u.active = True
        db.session.add(u)
        db.session.commit()

        captcha_code = "123456"
        cap = EmailCaptcha(email=email, captcha=captcha_code)
        db.session.add(cap)
        db.session.commit()

        return {"email": email, "captcha": captcha_code}


def test_reset_password_missing_fields_returns_400(client):
    rv = client.post("/password/reset/", json={})
    assert rv.status_code == 400
    assert rv.get_json()["code"] == 400


def test_reset_password_email_not_registered_returns_400(client):
    rv = client.post("/password/reset/", json={
        "email": "nobody@example.com",
        "captcha": "123456",
        "new_password": "new_pass"
    })
    assert rv.status_code == 400
    data = rv.get_json()
    assert data["code"] == 400
    assert "invalid" in data["message"].lower()

def test_reset_password_success_hashes_and_allows_login(client, app, user_and_captcha):
    email = user_and_captcha["email"]
    captcha_code = user_and_captcha["captcha"]

    rv = client.post("/password/reset/", json={
        "email": email,
        "captcha": captcha_code,
        "new_password": "brand_new_pass"
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["code"] == 200

    with app.app_context():
        fresh = User.query.filter_by(email=email).first()
        assert fresh is not None
        assert fresh.check_password("brand_new_pass") is True
        assert fresh.check_password("old_password") is False
