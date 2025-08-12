# tests/integration/test_settings_integration.py
from research_assistant.extensions import db
from research_assistant.user.models import User
from research_assistant.user_settings.models import UserSettings
from research_assistant.reference.models import Reference
from research_assistant.tag.models import Tag


def _mk_user(app, username="itguser", email="itg@example.com", password="Aa1234"):
    with app.app_context():
        u = User(username=username, email=email, password=password)
        db.session.add(u)
        db.session.commit()
        return u


def test_get_settings_autocreate_defaults(client, app, auth_header_app):
    u = _mk_user(app)
    r = client.get("/settings/", headers=auth_header_app(u.id))
    assert r.status_code == 200
    j = r.get_json()
    assert j["username"] == "itguser" and j["email"] == "itg@example.com"
    assert "language" in j and "theme" in j and "notifications_enabled" in j and "export_format" in j
    with app.app_context():
        assert UserSettings.query.filter_by(user_id=u.id).count() == 1


def test_update_settings_merge(client, app, auth_header_app):
    u = _mk_user(app)
    r = client.put(
        "/settings/",
        json={"language": "en", "theme": "dark", "notifications_enabled": True, "export_format": "docx"},
        headers=auth_header_app(u.id),
    )
    assert r.status_code == 200
    s = r.get_json()["settings"]
    assert s["language"] == "en" and s["theme"] == "dark" and s["notifications_enabled"] is True and s["export_format"] == "docx"
    r2 = client.put(
        "/settings/",
        json={"language": "zh"},
        headers=auth_header_app(u.id),
    )
    assert r2.status_code == 200
    s2 = r2.get_json()["settings"]
    assert s2["language"] == "zh" and s2["theme"] == "dark"


def test_update_profile_validation_and_conflicts(client, app, auth_header_app, monkeypatch):
    u1 = _mk_user(app, username="alice_itg", email="alice_itg@example.com")
    u2 = _mk_user(app, username="bob_itg", email="bob_itg@example.com")
    calls = {"sent": 0}
    import research_assistant.user_settings.views as views
    monkeypatch.setattr(views, "send_email", lambda *a, **k: calls.__setitem__("sent", calls["sent"] + 1) or True)

    r0 = client.put(
        "/settings/profile",
        json={"username": "", "email": ""},
        headers=auth_header_app(u1.id),
    )
    assert r0.status_code == 400

    r_bad_email = client.put(
        "/settings/profile",
        json={"username": "x", "email": "not-an-email"},
        headers=auth_header_app(u1.id),
    )
    assert r_bad_email.status_code == 400

    r_conflict_name = client.put(
        "/settings/profile",
        json={"username": "bob_itg", "email": "alice_new@example.com"},
        headers=auth_header_app(u1.id),
    )
    assert r_conflict_name.status_code == 409

    r_conflict_email = client.put(
        "/settings/profile",
        json={"username": "alice_new", "email": "bob_itg@example.com"},
        headers=auth_header_app(u1.id),
    )
    assert r_conflict_email.status_code == 409

    client.put(
        "/settings/",
        json={"notifications_enabled": True},
        headers=auth_header_app(u1.id),
    )
    r_ok = client.put(
        "/settings/profile",
        json={"username": "alice_new", "email": "alice_new@example.com"},
        headers=auth_header_app(u1.id),
    )
    assert r_ok.status_code == 200
    assert calls["sent"] >= 1


def test_change_password_paths(client, app, auth_header_app):
    u = _mk_user(app)
    r_missing = client.post(
        "/settings/change-password",
        json={"current_password": "", "new_password": ""},
        headers=auth_header_app(u.id),
    )
    assert r_missing.status_code == 400

    r_weak = client.post(
        "/settings/change-password",
        json={"current_password": "Aa1234", "new_password": "short"},
        headers=auth_header_app(u.id),
    )
    assert r_weak.status_code == 400

    r_wrong = client.post(
        "/settings/change-password",
        json={"current_password": "WrongOld", "new_password": "NewPassA"},
        headers=auth_header_app(u.id),
    )
    assert r_wrong.status_code == 401

    r_ok = client.post(
        "/settings/change-password",
        json={"current_password": "Aa1234", "new_password": "NewPassA"},
        headers=auth_header_app(u.id),
    )
    assert r_ok.status_code == 200


def test_delete_account_integration(client, app, auth_header_app, monkeypatch):
    u = _mk_user(app, username="del_itg", email="del_itg@example.com")
    with app.app_context():
        s = UserSettings(user_id=u.id, notifications_enabled=True)
        ref = Reference(title="R", authors="A, B.", year="2024", source="J", user_id=u.id)
        tag = Tag(name="T", user_id=u.id)
        db.session.add_all([s, ref, tag])
        db.session.commit()

    calls = {"sent": 0}
    import research_assistant.user_settings.views as views
    monkeypatch.setattr(views, "send_email", lambda *a, **k: calls.__setitem__("sent", calls["sent"] + 1) or True)

    r = client.delete("/settings/delete", headers=auth_header_app(u.id))
    assert r.status_code == 200
    assert calls["sent"] >= 1

    with app.app_context():
        assert User.query.get(u.id) is None
        assert Reference.query.filter_by(user_id=u.id).count() == 0
        assert Tag.query.filter_by(user_id=u.id).count() == 0
        assert UserSettings.query.filter_by(user_id=u.id).count() == 0
