# tests/e2e/test_outline_e2e.py
import pytest
from flask_jwt_extended import create_access_token

from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.outline.models import Section


@pytest.fixture(scope="module")
def app():
    """
    Create an isolated Flask app + in-memory DB for this module.
    """
    app = create_app("research_assistant.settings")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="outline-e2e-secret",
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
    Ensure a test user exists and return a Bearer JWT header.
    """
    with app.app_context():
        user = User.query.filter_by(email="outline_e2e@example.com").first()
        if not user:
            user = User(username="outline_e2e", email="outline_e2e@example.com")
            user.password = "pw"
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {token}"}


def test_outline_full_flow_e2e(client, auth_header, app):
    """
    End-to-end flow:
    1) Clean slate (remove all sections)
    2) Save a nested outline (two roots; first root has two children)
    3) Get all roots and verify structure
    4) Update a nested child section
    5) Get the updated child by ID and verify changes
    6) Delete a root section (cascades to children)
    7) Verify subtree is gone while the other root remains
    """
    # 1) Clean DB state for this E2E
    with app.app_context():
        Section.query.delete()
        _db.session.commit()

    # 2) Save a nested outline
    payload = {
        "outline": [
            {
                "title": "E2E Root 1",
                "summary": "root-1 summary",
                "subsections": [
                    {"title": "E2E Child 1.1", "summary": "child-1.1 summary"},
                    {"title": "E2E Child 1.2"},
                ],
            },
            {"title": "E2E Root 2"},
        ]
    }
    r_save = client.post("/outline/save", json=payload, headers=auth_header)
    assert r_save.status_code == 201
    assert r_save.get_json()["success"] is True

    # 3) Get all roots & verify
    r_roots = client.get("/outline/get", headers=auth_header)
    assert r_roots.status_code == 200
    roots = r_roots.get_json()["data"]
    assert len(roots) == 2

    # Locate by title for stability
    root1 = next(r for r in roots if r["title"] == "E2E Root 1")
    root2 = next(r for r in roots if r["title"] == "E2E Root 2")
    assert len(root1.get("subsections", [])) == 2

    # 4) Update a nested child (rename 1.1)
    child_11_id = root1["subsections"][0]["id"]
    r_upd = client.put(
        f"/update/{child_11_id}",
        json={"outline": {"title": "E2E Child 1.1 (renamed)"}},
        headers=auth_header,
    )
    assert r_upd.status_code == 200
    body_upd = r_upd.get_json()
    assert body_upd["success"] is True
    assert body_upd["data"]["title"] == "E2E Child 1.1 (renamed)"

    # 5) Get the updated child by ID & verify persisted change
    r_child = client.get(f"/outline/get/{child_11_id}", headers=auth_header)
    assert r_child.status_code == 200
    assert r_child.get_json()["data"]["title"] == "E2E Child 1.1 (renamed)"

    # 6) Delete the first root (should cascade delete its children)
    r_del = client.delete(f"/delete/{root1['id']}", headers=auth_header)
    assert r_del.status_code == 204

    # 7) Verify subtree is gone and the other root remains
    r_after = client.get("/outline/get", headers=auth_header)
    assert r_after.status_code == 200
    after_roots = r_after.get_json()["data"]

    # Helper: flatten remaining IDs
    def flatten_ids(nodes):
        for n in nodes:
            yield n["id"]
            for sub in n.get("subsections", []):
                yield from flatten_ids([sub])

    remaining_ids = set(flatten_ids(after_roots))
    assert child_11_id not in remaining_ids  # subtree removed
    assert any(n["title"] == "E2E Root 2" for n in after_roots)  # other root remains
