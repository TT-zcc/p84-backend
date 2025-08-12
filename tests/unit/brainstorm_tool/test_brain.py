# tests/test_brain.py

import pytest
import json
from datetime import datetime
from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.brain.models import BrainEntry
from flask_jwt_extended import create_access_token

@pytest.fixture(scope='session')
def app():
    # Configure test app with in-memory database
    app = create_app('research_assistant.settings')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
    })
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
    Reuse or create a single test user so that foreign-key updates
    do not conflict across tests.
    """
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(username='testuser', email='test@example.com', password='password')
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))
    return {'Authorization': f'Bearer {token}'}

def test_brainentry_model_to_dict(app):
    """Test the BrainEntry.to_dict() helper method."""
    with app.app_context():
        # Create a separate user to avoid cross-test collisions
        u = User(username='u1', email='u1@example.com', password='pwd')
        _db.session.add(u)
        _db.session.commit()

        msgs = [{'from':'user','text':'hello'}]
        entry = BrainEntry(
            why='Why?',
            what='What?',
            where='Where?',
            when='When?',
            who='Who?',
            messages=json.dumps(msgs),
            overall_feedback='Feedback.',
            completed=True,
            user_id=u.id
        )
        _db.session.add(entry)
        _db.session.commit()

        d = entry.to_dict()
        assert d['fiveW'] == {
            'why':'Why?',
            'what':'What?',
            'where':'Where?',
            'when':'When?',
            'who':'Who?'
        }
        assert d['messages'] == msgs
        assert d['overallFeedback'] == 'Feedback.'
        assert d['completed'] is True
        assert isinstance(d['created_at'], str)
        assert isinstance(d['updated_at'], str)

def test_save_brainstorm_session_endpoint(client, auth_header, app):
    """Test POST /brainstorm/save endpoint."""
    payload = {
        'fiveW': {
            'why': 'test why',
            'what': 'test what',
            'where': 'test where',
            'when': 'test when',
            'who': 'test who',
        },
        'messages': [{'from': 'user', 'text': 'msg'}],
        'overallFeedback': 'nice',
        'completed': False
    }
    resp = client.post('/brainstorm/save', json=payload, headers=auth_header)
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'id' in data

    # Verify data was saved in DB
    with app.app_context():
        e = _db.session.get(BrainEntry, data['id'])
        assert e is not None
        assert e.why == payload['fiveW']['why']
        assert e.what == payload['fiveW']['what']
        assert json.loads(e.messages) == payload['messages']
        assert e.overall_feedback == payload['overallFeedback']
        assert e.completed == payload['completed']

def test_load_brainstorm_session_endpoint(client, auth_header):
    """Test GET /brainstorm/load endpoint."""
    resp = client.get('/brainstorm/load', headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    # Should return either {} when empty or a valid entry dict
    assert isinstance(data, dict)
    if data:
        assert 'fiveW' in data
        assert 'messages' in data

@pytest.mark.parametrize('flag', [True, False])
def test_complete_brainstorm_step_endpoint(client, auth_header, flag):
    """Test POST /brainstorm/progress updates the completion flag."""
    # Ensure an entry exists first
    save_payload = {
        'fiveW': {'why':'a','what':'b','where':'c','when':'d','who':'e'},
        'messages': [], 'overallFeedback':'','completed':False
    }
    save_resp = client.post('/brainstorm/save', json=save_payload, headers=auth_header)
    assert save_resp.status_code == 201

    # Call the progress endpoint to toggle completion
    resp = client.post('/brainstorm/progress', json={'completed': flag}, headers=auth_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['completed'] is flag
