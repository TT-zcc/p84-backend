# tests/e2e/test_brainstorm_flow.py

import pytest
from flask_jwt_extended import create_access_token

from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.brain.models import BrainEntry
from research_assistant.planning.models import Phase, Task


# ---- Test App / Client / Auth Fixtures --------------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Build a test app with an in-memory database and a JWT secret.
    """
    app = create_app("research_assistant.settings")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="e2e-brainstorm-secret",
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
    Ensure a single dedicated E2E user exists and return its JWT header.
    """
    with app.app_context():
        user = User.query.filter_by(email="brain_e2e@example.com").first()
        if not user:
            user = User(username="brain_e2e", email="brain_e2e@example.com", password="pw")
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---- Helpers ----------------------------------------------------------------

def _clean_user_data(app):
    """
    Remove all BrainEntry/Phase/Task for the E2E user to start from a clean slate.
    """
    with app.app_context():
        user = User.query.filter_by(email="brain_e2e@example.com").first()
        if not user:
            return
        # Delete in an order that respects FKs: tasks -> phases -> brain entries
        Task.query.filter_by(user_id=user.id).delete()
        Phase.query.filter_by(user_id=user.id).delete()
        BrainEntry.query.filter_by(user_id=user.id).delete()
        _db.session.commit()


# ---- E2E Test ----------------------------------------------------------------

def test_brainstorm_full_flow_e2e(client, auth_header, app):
    """
    End-to-end flow:
      1) Clean slate (no BrainEntry/Phase/Task for the user)
      2) GET /brainstorm/load -> {}
      3) POST /brainstorm/save with incomplete 5W -> 201, no 'Brainstorm Complete' task created
      4) Create Phase('Define Topic & Question') for the user
      5) POST /brainstorm/save with complete 5W -> 201, 'Brainstorm Complete' task auto-created
      6) POST /brainstorm/progress completed=True -> flips flag, load shows completed
      7) POST /brainstorm/progress completed=False -> flips back, load shows not completed
    """
    _clean_user_data(app)

    # 2) Initially nothing saved
    r0 = client.get("/brainstorm/load", headers=auth_header)
    assert r0.status_code == 200
    assert r0.get_json() == {}

    # 3) Save an incomplete 5W payload: should NOT add the auto task
    incomplete_payload = {
        "fiveW": {
            "why": "why",
            "what": "what",
            "where": "where",
            "when": "when",
            # 'who' intentionally missing
        },
        "messages": [{"from": "user", "text": "hi"}],
        "overallFeedback": "ok",
        "completed": False,
    }
    r1 = client.post("/brainstorm/save", json=incomplete_payload, headers=auth_header)
    assert r1.status_code == 201
    assert "id" in r1.get_json()

    with app.app_context():
        user = User.query.filter_by(email="brain_e2e@example.com").first()
        user_id = user.id  # cache scalar to avoid DetachedInstanceError later

        last = (
            BrainEntry.query.filter_by(user_id=user_id)
            .order_by(BrainEntry.updated_at.desc())
            .first()
        )
        assert last is not None
        assert Task.query.filter_by(user_id=user_id).count() == 0

    # 4) Create the Phase that the brainstorm save hook expects
    with app.app_context():
        phase = Phase(title="Define Topic & Question", user_id=user_id)
        _db.session.add(phase)
        _db.session.commit()
        phase_id = phase.id  # cache scalar

    # 5) Save a complete 5W payload: should auto-append 'Brainstorm Complete' task to the phase
    complete_payload = {
        "fiveW": {
            "why": "why",
            "what": "what",
            "where": "where",
            "when": "when",
            "who": "who",
        },
        "messages": [{"from": "assistant", "text": "ack"}],
        "overallFeedback": "great",
        "completed": False,
    }
    r2 = client.post("/brainstorm/save", json=complete_payload, headers=auth_header)
    assert r2.status_code == 201
    entry_id = r2.get_json()["id"]
    assert isinstance(entry_id, int)

    # Verify the task was created (query by user_id or phase_id to avoid ORM detachment)
    with app.app_context():
        tasks = Task.query.filter_by(phase_id=phase_id).all()
        assert len(tasks) == 1
        t = tasks[0]
        assert t.description == "Brainstorm Complete"
        assert t.completed is True
        assert t.user_id == user_id

    # 6) Mark progress completed=True
    r3 = client.post("/brainstorm/progress", json={"completed": True}, headers=auth_header)
    assert r3.status_code == 200
    assert r3.get_json()["completed"] is True

    # Load latest entry and ensure the completed flag is true
    r4 = client.get("/brainstorm/load", headers=auth_header)
    assert r4.status_code == 200
    data4 = r4.get_json()
    assert data4 and data4.get("completed") is True

    # 7) Mark progress completed=False, then load again
    r5 = client.post("/brainstorm/progress", json={"completed": False}, headers=auth_header)
    assert r5.status_code == 200
    assert r5.get_json()["completed"] is False

    r6 = client.get("/brainstorm/load", headers=auth_header)
    assert r6.status_code == 200
    data6 = r6.get_json()
    assert data6 and data6.get("completed") is False
