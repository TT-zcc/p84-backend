from research_assistant.extensions import db
from research_assistant.tag.models import Tag
from research_assistant.reference.models import Reference


def test_add_tag_create_and_idempotent(client, auth_header_app, seed_docs):
    u1 = seed_docs["u1"].id
    r1 = client.post("/tags/", json={"name": "reading"}, headers=auth_header_app(u1))
    assert r1.status_code == 200
    tag_id = r1.get_json()["id"]
    r2 = client.post("/tags/", json={"name": "reading"}, headers=auth_header_app(u1))
    assert r2.status_code == 200
    assert r2.get_json()["id"] == tag_id


def test_add_tag_bad_request(client, auth_header_app, seed_docs):
    u1 = seed_docs["u1"].id
    r = client.post("/tags/", json={"name": "   "}, headers=auth_header_app(u1))
    assert r.status_code == 400


def test_list_tags_isolated(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    u2 = seed_docs["u2"].id
    with app.app_context():
        db.session.add_all([Tag(name="t1", user_id=u1), Tag(name="t2", user_id=u1), Tag(name="t3", user_id=u2)])
        db.session.commit()
    r1 = client.get("/tags/list", headers=auth_header_app(u1))
    names1 = sorted([x["name"] for x in r1.get_json()])
    assert names1 == ["t1", "t2"]
    r2 = client.get("/tags/list", headers=auth_header_app(u2))
    names2 = sorted([x["name"] for x in r2.get_json()])
    assert names2 == ["t3"]


def test_assign_tag_creates_if_missing_and_attach_once(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    doc_id = seed_docs["u1_doc_ids"][0]
    r1 = client.post("/tags/assign", json={"document_id": doc_id, "tag": "todo"}, headers=auth_header_app(u1))
    assert r1.status_code == 200
    r2 = client.post("/tags/assign", json={"document_id": doc_id, "tag": "todo"}, headers=auth_header_app(u1))
    assert r2.status_code == 200
    with app.app_context():
        d = Reference.query.get(doc_id)
        names = [t.name for t in d.tags]
        assert names.count("todo") == 1


def test_assign_tag_missing_params(client, auth_header_app, seed_docs):
    u1 = seed_docs["u1"].id
    r = client.post("/tags/assign", json={"document_id": None, "tag": ""}, headers=auth_header_app(u1))
    assert r.status_code == 400


def test_assign_tag_doc_not_found_or_no_permission(client, auth_header_app, seed_docs):
    u1_doc = seed_docs["u1_doc_ids"][0]
    u2 = seed_docs["u2"].id
    r = client.post("/tags/assign", json={"document_id": u1_doc, "tag": "oops"}, headers=auth_header_app(u2))
    assert r.status_code == 404


def test_get_all_docs_with_tags(client, auth_header_app, seed_docs):
    u1 = seed_docs["u1"].id
    d1, d2 = seed_docs["u1_doc_ids"]
    client.post("/tags/assign", json={"document_id": d1, "tag": "reading"}, headers=auth_header_app(u1))
    client.post("/tags/assign", json={"document_id": d2, "tag": "ml"}, headers=auth_header_app(u1))
    r = client.get("/tags/all-docs-with-tags", headers=auth_header_app(u1))
    assert r.status_code == 200
    arr = r.get_json()
    assert isinstance(arr, list) and len(arr) >= 2
    doc_ids = {x["id"] for x in arr}
    assert d1 in doc_ids and d2 in doc_ids
    for x in arr:
        assert "tags" in x and isinstance(x["tags"], list)


def test_remove_tag_from_document_flow(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    d1 = seed_docs["u1_doc_ids"][0]
    client.post("/tags/assign", json={"document_id": d1, "tag": "temp"}, headers=auth_header_app(u1))
    with app.app_context():
        tag = Tag.query.filter_by(name="temp", user_id=u1).first()
        tag_id = tag.id
    r2 = client.delete("/tags/remove", json={"document_id": d1, "tag_id": tag_id}, headers=auth_header_app(u1))
    assert r2.status_code == 200
    r3 = client.delete("/tags/remove", json={"document_id": d1, "tag_id": tag_id}, headers=auth_header_app(u1))
    assert r3.status_code == 400


def test_remove_tag_unauthorized(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    u2 = seed_docs["u2"].id
    d1 = seed_docs["u1_doc_ids"][0]
    client.post("/tags/assign", json={"document_id": d1, "tag": "x"}, headers=auth_header_app(u1))
    with app.app_context():
        tag = Tag.query.filter_by(name="x", user_id=u1).first()
    r = client.delete("/tags/remove", json={"document_id": d1, "tag_id": tag.id}, headers=auth_header_app(u2))
    assert r.status_code == 404


def test_tag_stats_counts(client, auth_header_app, seed_docs):
    u1 = seed_docs["u1"].id
    d1, d2 = seed_docs["u1_doc_ids"]
    client.post("/tags/assign", json={"document_id": d1, "tag": "a"}, headers=auth_header_app(u1))
    client.post("/tags/assign", json={"document_id": d2, "tag": "a"}, headers=auth_header_app(u1))
    client.post("/tags/assign", json={"document_id": d2, "tag": "b"}, headers=auth_header_app(u1))
    r = client.get("/tags/stats", headers=auth_header_app(u1))
    stats = {x["tag"]: x["count"] for x in r.get_json()}
    assert stats.get("a") == 2
    assert stats.get("b") == 1


def test_mark_document_complete_toggle(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    d1 = seed_docs["u1_doc_ids"][0]
    r1 = client.post("/tags/mark-complete", json={"document_id": d1, "completed": True}, headers=auth_header_app(u1))
    assert r1.status_code == 200
    with app.app_context():
        assert Reference.query.get(d1).completed is True
    r2 = client.post("/tags/mark-complete", json={"document_id": d1, "completed": False}, headers=auth_header_app(u1))
    assert r2.status_code == 200
    with app.app_context():
        assert Reference.query.get(d1).completed is False


def test_mark_document_complete_no_permission(client, auth_header_app, seed_docs):
    u2 = seed_docs["u2"].id
    u1_doc = seed_docs["u1_doc_ids"][0]
    r = client.post("/tags/mark-complete", json={"document_id": u1_doc, "completed": True}, headers=auth_header_app(u2))
    assert r.status_code == 404


def test_update_tag_name_success_and_perm(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    u2 = seed_docs["u2"].id
    with app.app_context():
        t = Tag(name="old", user_id=u1)
        db.session.add(t)
        db.session.commit()
        tag_id = t.id
    r1 = client.put("/tags/update", json={"tag_id": tag_id, "new_name": "new"}, headers=auth_header_app(u1))
    assert r1.status_code == 200
    r2 = client.put("/tags/update", json={"tag_id": tag_id, "new_name": "xxx"}, headers=auth_header_app(u2))
    assert r2.status_code == 404


def test_delete_tag_removes_associations(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    d1 = seed_docs["u1_doc_ids"][0]
    client.post("/tags/assign", json={"document_id": d1, "tag": "will_del"}, headers=auth_header_app(u1))
    with app.app_context():
        t = Tag.query.filter_by(name="will_del", user_id=u1).first()
        tag_id = t.id
    r = client.delete("/tags/delete", json={"tag_id": tag_id}, headers=auth_header_app(u1))
    assert r.status_code == 200
    with app.app_context():
        assert Tag.query.get(tag_id) is None
        d1_obj = Reference.query.get(d1)
        assert all(t.name != "will_del" for t in d1_obj.tags)


def test_delete_tag_no_permission(client, auth_header_app, seed_docs, app):
    u1 = seed_docs["u1"].id
    u2 = seed_docs["u2"].id
    r = client.post("/tags/", json={"name": "mine"}, headers=auth_header_app(u1))
    tag_id = r.get_json()["id"]
    r2 = client.delete("/tags/delete", json={"tag_id": tag_id}, headers=auth_header_app(u2))
    assert r2.status_code == 404
