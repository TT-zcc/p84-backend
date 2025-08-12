# tests/conftest.py
# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
from unittest.mock import MagicMock

import pytest
from flask_jwt_extended import create_access_token
from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.reference.models import Reference
from research_assistant.tag.models import Tag

@pytest.fixture
def app():
    """Create a Flask app instance for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "DEBUG_TB_ENABLED": False,
        "JWT_SECRET_KEY": "test-secret-key",  # Needed for JWT
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Provide the database instance."""
    return _db


@pytest.fixture
def client(app):
    """Provide Flask test client."""
    return app.test_client()


@pytest.fixture
def test_user(db):
    user = User(username="testuser", email="test@example.com", password="123456")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_client(client, test_user):
    token = create_access_token(identity=str(test_user.id)) 
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client

@pytest.fixture(autouse=True)
def mock_s3_upload(monkeypatch):
    """Mock S3 upload globally for all tests."""
    def fake_upload(file, key):
        return f"https://mock-s3/{key}"
    # Patch both the utils function and the imported reference in routes
    monkeypatch.setattr("research_assistant.utils.upload_file_to_s3", fake_upload, raising=True)
    monkeypatch.setattr("research_assistant.writing_tool.routes.upload_file_to_s3", fake_upload, raising=True)

@pytest.fixture
def mock_s3_client_obj():
    """Provide a mocked S3 client for tests (no pytest-mock required)."""
    mocked_client = MagicMock()
    mocked_client.generate_presigned_url.return_value = "https://mock-presigned-url"
    mocked_client.delete_object.return_value = None
    return mocked_client

@pytest.fixture
def users_two(db):
    u1 = User(username="alice", email="alice@example.com", password="123456")
    u2 = User(username="bob",   email="bob@example.com",   password="123456")
    db.session.add_all([u1, u2])
    db.session.commit()
    return u1, u2

@pytest.fixture
def auth_header_app():
    def _make(user_id: int):
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}
    return _make

@pytest.fixture
def seed_refs(app, db, users_two):
    u1, u2 = users_two
    r1 = Reference(title="Alpha", authors="Zhang, W.; Li, H.", year="2020", source="ICML",    user_id=u1.id)
    r2 = Reference(title="Beta",  authors="Wang, X.",          year="2021", source="NeurIPS", user_id=u1.id)
    r3 = Reference(title="Gamma", authors="Doe, J.; Roe, R.",  year="2019", source="KDD",     user_id=u2.id)
    db.session.add_all([r1, r2, r3])
    db.session.commit()
    return {"u1": u1, "u2": u2, "u1_ids": [r1.id, r2.id], "u2_ids": [r3.id]}

@pytest.fixture
def seed_docs(seed_refs):
    return {
        "u1": seed_refs["u1"],
        "u2": seed_refs["u2"],
        "u1_doc_ids": seed_refs["u1_ids"],
        "u2_doc_ids": seed_refs["u2_ids"],
    }

@pytest.fixture
def sample_bib_file():
    import io
    content = r"""
@article{key1,
  title   = { {Deep} Learning in Vision },
  author  = {Goodfellow, I. and Bengio, Y. and Courville, A.},
  year    = {2016},
  journal = {Nature}
}

@article{key2,
  title   = {Graph {N}etworks},
  author  = {Kipf, T. and Welling, M.},
  year    = {2017},
  journal = {ICLR}
}

@inproceedings{skip_me,
  title   = {Not an article},
  author  = {Someone, A.},
  year    = {2018},
  booktitle = {Somewhere}
}
""".strip()
    f = io.BytesIO(content.encode("utf-8"))
    f.name = "refs.bib"
    return f
