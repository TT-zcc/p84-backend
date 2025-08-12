# tests/e2e/test_planning_flow.py
import pytest
from flask_jwt_extended import create_access_token

from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.outline.models import Section
from research_assistant.planning.models import Phase, Task


@pytest.fixture(scope="session")
def app():
    app = create_app("research_assistant.settings")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="e2e-planning-secret",
        WTF_CSRF_ENABLED=False,
        PROPAGATE_EXCEPTIONS=True,
    )
    with app.app_context():
        _db.create_all()
    yield app
    with app.app_context():
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    """
    Create a dedicated E2E user and issue a JWT for requests.
    """
    with app.app_context():
        user = User.query.filter_by(email="plan_e2e@example.com").first()
        if not user:
            user = User(username="plan_e2e", email="plan_e2e@example.com")
            user.password = "pw"
            user.active = True
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _clean_user_data(app):
    """
    Remove all planning/outline data for the E2E user to avoid cross-test pollution.
    """
    with app.app_context():
        user = User.query.filter_by(email="plan_e2e@example.com").first()
        assert user is not None

        # Deletion order matters: delete Tasks first, then Phases; Sections are managed separately.
        Task.query.filter_by(user_id=user.id).delete()
        Phase.query.filter_by(user_id=user.id).delete()
        Section.query.filter_by(user_id=user.id).delete()
        _db.session.commit()


def test_planning_full_flow_e2e(client, auth_header, app):
    """
    End-to-end flow:
      1) Wipe user data for a clean slate
      2) POST /planning/ to save sections + timeline (two phases, multiple tasks)
      3) GET /planning/ and validate structure and computed stats
      4) PATCH /planning/<phase_id>/tasks/<task_id> to toggle completion and validate stats update
      5) DELETE /planning/<phase_id> to remove one phase and validate the other remains
      6) DELETE the remaining phase and validate timeline becomes empty while sections remain
    """
    _clean_user_data(app)

    # 2) Save one root section and two phases
    payload = {
        "sections": [
            {
                "title": "S1",
                "summary": "S1 summary",
                "subsections": [
                    {"title": "S1-1", "summary": "S1-1 summary"},
                ],
            }
        ],
        "timeline": [
            {
                "title": "Phase A",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "deadline": "2025-01-04",
                "tasks": [
                    {"description": "A-Task 1", "completed": False},
                    {"description": "A-Task 2", "completed": True},
                ],
            },
            {
                "title": "Phase B",
                "start_date": "2025-02-01",
                "end_date": "2025-02-10",
                "deadline": "2025-02-09",
                "tasks": [
                    {"description": "B-Task 1", "completed": True},
                ],
            },
        ],
    }
    r_save = client.post("/planning/", json=payload, headers=auth_header)
    assert r_save.status_code == 200
    assert r_save.get_json()["msg"] == "Planning saved"

    # 3) Fetch and validate
    r_get = client.get("/planning/", headers=auth_header)
    assert r_get.status_code == 200
    body = r_get.get_json()

    # Sections
    assert len(body["sections"]) == 1
    assert body["sections"][0]["title"] == "S1"
    assert len(body["sections"][0]["subsections"]) == 1

    # Timeline basics
    assert len(body["timeline"]) == 2
    pha, phb = body["timeline"][0], body["timeline"][1]
    assert pha["title"] == "Phase A"
    assert phb["title"] == "Phase B"

    # Computed stats
    assert pha["total_tasks"] == 2
    assert pha["completed_tasks"] == 1
    assert phb["total_tasks"] == 1
    assert phb["completed_tasks"] == 1

    # 4) Toggle Phase A's first task (False -> True)
    phase_a_id = pha["id"]
    task_a1_id = pha["tasks"][0]["id"]
    r_toggle = client.patch(f"/planning/{phase_a_id}/tasks/{task_a1_id}", headers=auth_header)
    assert r_toggle.status_code == 200
    assert r_toggle.get_json()["completed"] is True

    # Stats should now be 2/2 for Phase A
    r_get2 = client.get("/planning/", headers=auth_header)
    pha2 = r_get2.get_json()["timeline"][0]
    assert pha2["completed_tasks"] == 2
    assert pha2["total_tasks"] == 2

    # 5) Delete Phase B and ensure only Phase A remains
    phase_b_id = phb["id"]
    r_del_b = client.delete(f"/planning/{phase_b_id}", headers=auth_header)
    assert r_del_b.status_code == 200
    left = client.get("/planning/", headers=auth_header).get_json()["timeline"]
    assert len(left) == 1
    assert left[0]["id"] == phase_a_id

    # 6) Delete Phase A; timeline should be empty while sections remain intact
    r_del_a = client.delete(f"/planning/{phase_a_id}", headers=auth_header)
    assert r_del_a.status_code == 200

    r_after = client.get("/planning/", headers=auth_header).get_json()
    assert r_after["timeline"] == []
    assert len(r_after["sections"]) == 1  # sections should still be present
