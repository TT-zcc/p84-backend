# tests/integration/test_planning_extra.py

import pytest
from flask_jwt_extended import create_access_token

from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.outline.models import Section
from research_assistant.planning.models import Phase, Task


# -------------------- Fixtures --------------------

@pytest.fixture(scope="module")
def app():
    """
    Build a minimal test app with an in-memory DB and JWT secret.
    This fixture is module-scoped to keep tests isolated and fast.
    """
    app = create_app("research_assistant.settings")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="planning-extra-secret",
    )
    with app.app_context():
        _db.create_all()
    yield app
    with app.app_context():
        _db.drop_all()


@pytest.fixture
def auth_client(app):
    """
    Return a tiny client wrapper that automatically attaches a valid JWT
    for a dedicated planning E2E user.
    """
    client = app.test_client()
    with app.app_context():
        user = User.query.filter_by(email="planning_extra@example.com").first()
        if not user:
            user = User(username="planning_extra", email="planning_extra@example.com", password="pw")
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))

    class _AuthClient:
        def __init__(self, _client, _token):
            self._c = _client
            self._h = {"Authorization": f"Bearer {_token}"}

        def get(self, url, **kw):
            kw.setdefault("headers", {}).update(self._h)
            return self._c.get(url, **kw)

        def post(self, url, **kw):
            kw.setdefault("headers", {}).update(self._h)
            return self._c.post(url, **kw)

        def delete(self, url, **kw):
            kw.setdefault("headers", {}).update(self._h)
            return self._c.delete(url, **kw)

        def patch(self, url, **kw):
            kw.setdefault("headers", {}).update(self._h)
            return self._c.patch(url, **kw)

    return _AuthClient(client, token)


# -------------------- Helpers --------------------

def _wipe_user_data(app):
    """Remove all Sections/Tasks/Phases for the dedicated user."""
    with app.app_context():
        user = User.query.filter_by(email="planning_extra@example.com").first()
        if not user:
            return
        Task.query.filter_by(user_id=user.id).delete()
        Phase.query.filter_by(user_id=user.id).delete()
        Section.query.filter_by(user_id=user.id).delete()
        _db.session.commit()


# -------------------- Tests --------------------

def test_save_overwrites_previous_data(auth_client, app):
    """
    Saving planning data replaces any prior user data for both sections and timeline.
    """
    _wipe_user_data(app)

    # First save: 2 phases
    resp1 = auth_client.post(
        "/planning/",
        json={
            "sections": [{"title": "S1"}],
            "timeline": [
                {"title": "P1", "start_date": None, "end_date": None, "deadline": None, "tasks": []},
                {"title": "P2", "start_date": None, "end_date": None, "deadline": None, "tasks": []},
            ],
        },
    )
    assert resp1.status_code == 200

    data1 = auth_client.get("/planning/").get_json()
    assert len(data1["timeline"]) == 2
    assert [p["title"] for p in data1["timeline"]] == ["P1", "P2"]

    # Second save: overwritten with 1 phase
    resp2 = auth_client.post(
        "/planning/",
        json={
            "sections": [{"title": "S2"}],
            "timeline": [
                {
                    "title": "Only Phase",
                    "start_date": None,
                    "end_date": None,
                    "deadline": None,
                    "tasks": [{"description": "T1"}],
                }
            ],
        },
    )
    assert resp2.status_code == 200

    data2 = auth_client.get("/planning/").get_json()
    assert [p["title"] for p in data2["timeline"]] == ["Only Phase"]
    assert data2["sections"][0]["title"] == "S2"
    assert data2["timeline"][0]["total_tasks"] == 1


def test_delete_phase_cascades_tasks(auth_client, app):
    """
    Deleting a phase removes its tasks as well (cascade behavior).
    """
    _wipe_user_data(app)

    # Save one phase with two tasks
    save = auth_client.post(
        "/planning/",
        json={
            "sections": [],
            "timeline": [
                {
                    "title": "Phase A",
                    "start_date": None,
                    "end_date": None,
                    "deadline": None,
                    "tasks": [
                        {"description": "A-1", "completed": False},
                        {"description": "A-2", "completed": True},
                    ],
                }
            ],
        },
    )
    assert save.status_code == 200

    fetched = auth_client.get("/planning/").get_json()
    phase_id = fetched["timeline"][0]["id"]
    assert len(fetched["timeline"][0]["tasks"]) == 2

    # Delete the phase
    d = auth_client.delete(f"/planning/{phase_id}")
    assert d.status_code == 200

    # Timeline should be empty and underlying tasks should be gone
    after = auth_client.get("/planning/").get_json()
    assert after["timeline"] == []

    with app.app_context():
        assert Task.query.count() == 0


def test_toggle_task_404_for_invalid(auth_client, app):
    """
    Toggling a non-existent task for a valid phase returns 404.
    """
    _wipe_user_data(app)

    # Save a single phase with a single task
    auth_client.post(
        "/planning/",
        json={
            "sections": [],
            "timeline": [
                {
                    "title": "Phase X",
                    "start_date": None,
                    "end_date": None,
                    "deadline": None,
                    "tasks": [{"description": "Do X", "completed": False}],
                }
            ],
        },
    )

    phase = auth_client.get("/planning/").get_json()["timeline"][0]
    phase_id = phase["id"]

    # Use a bogus task id
    r = auth_client.patch(f"/planning/{phase_id}/tasks/999999")
    assert r.status_code == 404


def test_sections_tree_is_persisted(auth_client, app):
    """
    Sections are re-created as a proper tree when saving and returned nested on fetch.
    """
    _wipe_user_data(app)

    payload = {
        "sections": [
            {
                "title": "Root A",
                "summary": "root-a",
                "subsections": [
                    {"title": "A.1", "summary": "a1"},
                    {"title": "A.2", "summary": "a2", "subsections": [{"title": "A.2.a"}]},
                ],
            },
            {"title": "Root B"},
        ],
        "timeline": [],
    }
    s = auth_client.post("/planning/", json=payload)
    assert s.status_code == 200

    got = auth_client.get("/planning/").get_json()
    roots = got["sections"]
    assert [r["title"] for r in roots] == ["Root A", "Root B"]
    assert [c["title"] for c in roots[0]["subsections"]] == ["A.1", "A.2"]
    assert roots[0]["subsections"][1]["subsections"][0]["title"] == "A.2.a"
