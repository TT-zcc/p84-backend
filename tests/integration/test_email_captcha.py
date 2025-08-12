import json
import re
import pytest

from flask_mail import Message
from research_assistant.app import create_app
from research_assistant.extensions import db, mail
from research_assistant.user.models import EmailCaptcha


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        MAIL_SUPPRESS_SEND=True,
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


def test_send_email_captcha_missing_email_returns_400(client):
    rv = client.get("/captcha/email/")
    assert rv.status_code == 400
    data = rv.get_json()
    assert data["code"] == 400

    rv = client.post("/captcha/email/", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert data["code"] == 400


def test_send_email_captcha_success_creates_record_and_sends(client, app):
    target_email = "tester@example.com"

    with mail.record_messages() as outbox:
        rv = client.post("/captcha/email/", json={"email": target_email})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["code"] == 200

        rec = EmailCaptcha.query.filter_by(email=target_email).order_by(EmailCaptcha.created_at.desc()).first()
        assert rec is not None
        assert re.fullmatch(r"\d{6}", rec.captcha)  # 6 位数字

        assert len(outbox) == 1
        msg: Message = outbox[0]
        assert target_email in msg.recipients
        assert "Verification Code" in msg.subject
        assert rec.captcha in msg.body


def test_send_email_captcha_mail_failure_returns_500(monkeypatch, client):
    def boom(_msg):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr("research_assistant.public.views.mail.send", boom)

    rv = client.post("/captcha/email/", json={"email": "x@example.com"})
    assert rv.status_code == 500
    data = rv.get_json()
    assert data["code"] == 500
