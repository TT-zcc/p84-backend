# tests/e2e/test_settings_e2e.py
from research_assistant.extensions import db
from research_assistant.user.models import User
from research_assistant.user_settings.models import UserSettings
from research_assistant.reference.models import Reference
from research_assistant.tag.models import Tag


def _mk_user(app, username="e2euser", email="e2e@example.com", password="Aa1234"):
    with app.app_context():
        u = User(username=username, email=email, password=password)
        db.session.add(u)
        db.session.commit()
        return u


def test_settings_full_e2e_flow(client, app, auth_header_app, monkeypatch):
    u = _mk_user(app)

    calls = {"sent": 0}
    import research_assistant.user_settings.views as views
    monkeypatch.setattr(views, "send_email", lambda *a, **k: calls.__setitem__("sent", calls["sent"] + 1) or True)

    r = client.get("/settings/", headers=auth_header_app(u.id))
    assert r.status_code == 200
    j = r.get_json()
    assert j["username"] == "e2euser"
    assert j["email"] == "e2e@example.com"
    assert "language" in j and "theme" in j and "notifications_enabled" in j and "export_format" in j

    r2 = client.put(
        "/settings/",
        json={"language": "zh", "theme": "dark", "notifications_enabled": True, "export_format": "docx"},
        headers=auth_header_app(u.id),
    )
    assert r2.status_code == 200
    s = r2.get_json()["settings"]
    assert s["language"] == "zh" and s["theme"] == "dark" and s["notifications_enabled"] is True and s["export_format"] == "docx"

    r3 = client.put(
        "/settings/profile",
        json={"username": "e2euser2", "email": "e2e2@example.com", "notifications_enabled": True},
        headers=auth_header_app(u.id),
    )
    assert r3.status_code == 200
    jj = r3.get_json()
    assert jj["username"] == "e2euser2" and jj["email"] == "e2e2@example.com"
    assert calls["sent"] >= 1

    r_bad = client.post(
        "/settings/change-password",
        json={"current_password": "wrong", "new_password": "NewPassA"},
        headers=auth_header_app(u.id),
    )
    assert r_bad.status_code == 401

    r_ok = client.post(
        "/settings/change-password",
        json={"current_password": "Aa1234", "new_password": "NewPassA"},
        headers=auth_header_app(u.id),
    )
    assert r_ok.status_code == 200

    with app.app_context():
        ref = Reference(title="R", authors="A, B.", year="2024", source="J", user_id=u.id)
        tag = Tag(name="T", user_id=u.id)
        db.session.add_all([ref, tag])
        db.session.commit()

    r_del = client.delete("/settings/delete", headers=auth_header_app(u.id))
    assert r_del.status_code == 200

    with app.app_context():
        assert User.query.get(u.id) is None
        assert Reference.query.filter_by(user_id=u.id).count() == 0
        assert Tag.query.filter_by(user_id=u.id).count() == 0
        assert UserSettings.query.filter_by(user_id=u.id).count() == 0
