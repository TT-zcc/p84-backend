import pytest
import json
from research_assistant.app import create_app
from research_assistant.extensions import db as _db
from research_assistant.user.models import User
from research_assistant.outline.models import Section
from flask_jwt_extended import create_access_token

@pytest.fixture(scope='session')
def app():
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
    # Ensure a test user exists and generate a JWT for them
    with app.app_context():
        user = User.query.filter_by(email='outline_test@example.com').first()
        if not user:
            user = User(username='outline_test', email='outline_test@example.com', password='pw')
            _db.session.add(user)
            _db.session.commit()
        token = create_access_token(identity=str(user.id))
    return {'Authorization': f'Bearer {token}'}

def test_get_empty_outline(client, auth_header):
    # A GET on an empty outline should return an empty data list
    resp = client.get('/outline/get', headers=auth_header)
    assert resp.status_code == 200
    assert resp.get_json() == {'success': True, 'data': []}

def test_save_outline_options(client, auth_header):
    # The OPTIONS preflight request to the save endpoint should return HTTP 200
    resp = client.options('/outline/save', headers=auth_header)
    assert resp.status_code == 200

def test_save_outline_invalid(client, auth_header):
    # Saving an empty outline should return HTTP 400 with an error message
    resp = client.post('/outline/save', json={'outline': []}, headers=auth_header)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['success'] is False
    # English error message expected
    assert 'Cannot save empty outline!' in body['message']

def test_save_and_get_outline(client, auth_header):
    # Save a nested outline structure, then retrieve all and individual sections
    payload = {
        'outline': [
            {
                'title': 'Chapter 1',
                'summary': 'Chapter 1 summary',
                'subsections': [
                    {'title': 'Section 1.1', 'summary': 'Section 1.1 summary'},
                    {'title': 'Section 1.2'}
                ]
            },
            {'title': 'Chapter 2'}
        ]
    }
    # Save the outline
    resp = client.post('/outline/save', json=payload, headers=auth_header)
    assert resp.status_code == 201
    assert resp.get_json()['success'] is True

    # Retrieve all root sections
    resp_all = client.get('/outline/get', headers=auth_header)
    assert resp_all.status_code == 200
    body_all = resp_all.get_json()
    roots = body_all['data']
    assert len(roots) == 2
    assert roots[0]['title'] == 'Chapter 1'
    assert len(roots[0]['subsections']) == 2

    # Retrieve a single section by ID
    sec_id = roots[1]['id']
    resp_one = client.get(f'/outline/get/{sec_id}', headers=auth_header)
    assert resp_one.status_code == 200
    body_one = resp_one.get_json()
    assert body_one['data']['title'] == 'Chapter 2'
    assert body_one['data']['subsections'] == []

@pytest.mark.parametrize("field,upd_data,value", [
    ("title",   {"title": "New Chapter Title"},     "New Chapter Title"),
    ("summary", {"summary": "New summary"},           "New summary"),
    ("order",   {"order": 5},                         5),
])
def test_update_outline(client, auth_header, field, upd_data, value):
    # Save a simple outline to test updates
    client.post('/outline/save', json={'outline': [{'title': 'Original Chapter'}]}, headers=auth_header)
    get_resp = client.get('/outline/get', headers=auth_header)
    sec_id = get_resp.get_json()['data'][0]['id']

    # Perform the update
    resp_upd = client.put(f'/update/{sec_id}', json={'outline': upd_data}, headers=auth_header)
    assert resp_upd.status_code == 200
    body = resp_upd.get_json()
    assert body['success'] is True
    assert body['data'][field] == value

def test_delete_outline(client, auth_header):
    # Create then delete a section
    client.post('/outline/save', json={'outline': [{'title': 'Delete Me'}]}, headers=auth_header)
    get_resp = client.get('/outline/get', headers=auth_header)
    sec_id = get_resp.get_json()['data'][0]['id']

    # Delete the section
    resp_del = client.delete(f'/delete/{sec_id}', headers=auth_header)
    assert resp_del.status_code == 204

    # Confirm the section no longer exists
    after = client.get('/outline/get', headers=auth_header).get_json()['data']
    assert not any(s['id'] == sec_id for s in after)