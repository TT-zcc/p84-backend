import io
from docx import Document
from research_assistant.reference.models import Reference
from research_assistant.extensions import db


from research_assistant.reference.views import (
    format_authors_apa,
    format_authors_chicago,
    format_authors_mla,
    strip_doi_prefix,
    _clean_braced,
    build_docx_citation,
)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_add_reference_success(client, auth_header_app, seed_refs):
    user_id = seed_refs["u1"].id
    payload = {"title": "New Paper", "authors": "Smith, J.; Lee, K.", "year": "2022", "source": "CVPR"}
    resp = client.post("/references/", json=payload, headers=auth_header_app(user_id))
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "New Paper"
    r = client.get("/references/", headers=auth_header_app(user_id))
    assert r.status_code == 200
    assert any(x["title"] == "New Paper" for x in r.get_json())



def test_add_reference_missing_fields(client, auth_header_app, seed_refs):
    user_id = seed_refs["u1"].id
    resp = client.post("/references/", json={"title": "x"}, headers=auth_header_app(user_id))
    assert resp.status_code == 400
    assert "Missing fields" in resp.get_json().get("error", "")


def test_list_references_sorted_and_isolated(client, auth_header_app, seed_refs):
    u1 = seed_refs["u1"]
    r = client.get("/references/?sort_by=title", headers=auth_header_app(u1.id))
    assert r.status_code == 200
    titles = [x["title"] for x in r.get_json()]
    assert titles == sorted(titles)
    u2 = seed_refs["u2"]
    r2 = client.get("/references/", headers=auth_header_app(u2.id))
    assert r2.status_code == 200
    arr = r2.get_json()
    assert len(arr) == 1
    assert arr[0]["title"] == "Gamma"





def test_update_reference_success_and_forbidden(client, auth_header_app, seed_refs, app):
    u1 = seed_refs["u1"]
    u2 = seed_refs["u2"]
    r1_id = seed_refs["u1_ids"][0]


    resp = client.put(
        f"/references/{r1_id}",
        json={"title": "Alpha-Updated", "completed": True},
        headers=auth_header_app(u1.id),
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Alpha-Updated"
    assert resp.get_json()["completed"] is True

    resp2 = client.put(
        f"/references/{r1_id}",
        json={"title": "Hacked"},
        headers=auth_header_app(u2.id),
    )
    assert resp2.status_code == 404


def test_delete_reference(client, auth_header_app, seed_refs, app):
    u1 = seed_refs["u1"]
    r1_id = seed_refs["u1_ids"][0]
    resp = client.delete(f"/references/{r1_id}", headers=auth_header_app(u1.id))
    assert resp.status_code == 200

    with app.app_context():
        assert Reference.query.get(r1_id) is None


def test_upload_bib_success(client, auth_header_app, sample_bib_file, seed_refs, app):
    u1 = seed_refs["u1"]
    data = {"file": (sample_bib_file, "refs.bib")}
    resp = client.post("/references/upload_bib", data=data, headers=auth_header_app(u1.id),
                       content_type="multipart/form-data")
    assert resp.status_code == 201
    payload = resp.get_json()

    assert payload["count"] == 2
    titles = [c["title"] for c in payload["created"]]
    assert "Deep Learning in Vision" in titles
    assert "Graph N etworks" not in titles 

    with app.app_context():
        cnt = Reference.query.filter_by(user_id=u1.id).count()
        assert cnt >= 2


def test_upload_bib_no_file(client, auth_header_app, seed_refs):
    u1 = seed_refs["u1"]
    resp = client.post("/references/upload_bib", data={}, headers=auth_header_app(u1.id),
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "No file" in resp.get_json().get("error", "")


def test_generate_citation_docx_success(client, auth_header_app, seed_refs):
    u1 = seed_refs["u1"]
    r1_id = seed_refs["u1_ids"][0]
    for style in ("APA", "CHICAGO", "MLA"):
        resp = client.get(f"/references/{r1_id}/cite?style={style}", headers=auth_header_app(u1.id))
        assert resp.status_code == 200
        assert resp.mimetype == DOCX_MIME

        cd = resp.headers.get("Content-Disposition", "")
        assert cd.startswith("attachment;")
        assert cd.endswith(".docx")


def test_generate_citation_bad_style(client, auth_header_app, seed_refs):
    u1 = seed_refs["u1"]
    r1_id = seed_refs["u1_ids"][0]
    resp = client.get(f"/references/{r1_id}/cite?style=HARVARD", headers=auth_header_app(u1.id))
    assert resp.status_code == 400
    assert "Unsupported style" in resp.get_json().get("error", "")


def test_clean_braced():
    assert _clean_braced("{Hello}") == "Hello"
    assert _clean_braced("{{A}}") == "A"
    assert _clean_braced("NoBrace") == "NoBrace"


def test_strip_doi_prefix():
    assert strip_doi_prefix("https://doi.org/10.1000/xyz") == "10.1000/xyz"
    assert strip_doi_prefix("DOI:10.1/abc") == "10.1/abc"
    assert strip_doi_prefix("10.2/def") == "10.2/def"


def test_author_formatting_apa():
    assert format_authors_apa("A, B.; C, D.") == "A, B. & C, D."
    assert format_authors_apa("A, B.") == "A, B."
    assert format_authors_apa("A, B.; C, D.; E, F.") == "A, B., C, D., & E, F."


def test_author_formatting_chicago():

    assert format_authors_chicago("Zhang, Wei") == "Zhang, Wei"

    assert format_authors_chicago("Zhang, Wei; Li, Hua") == "Zhang, Wei and Hua Li"

    s = format_authors_chicago("Zhang, Wei; Li, Hua; Wang, Xiao")
    assert s == "Zhang, Wei, Hua Li, and Xiao Wang"


def test_author_formatting_mla():
    assert format_authors_mla("Zhang, Wei") == "Zhang, Wei"
    assert format_authors_mla("Zhang, Wei; Li, Hua") == "Zhang, Wei, and Hua Li"
    assert format_authors_mla("Zhang, Wei; Li, Hua; Wang, Xiao") == "Zhang, Wei, et al."


def test_build_docx_citation_memory_file(seed_refs, app):

    with app.app_context():
        r = Reference.query.get(seed_refs["u1_ids"][0])
        bio, name = build_docx_citation(r, "APA")
        assert name.endswith(".docx")
        doc = Document(bio)
        assert len(doc.paragraphs) >= 1
