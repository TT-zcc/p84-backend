# tests/test_planning.py
import pytest

# Assumes fixtures like auth_client and test_user are configured in the project,
# and auth_client automatically includes a valid JWT in its requests.

@pytest.fixture
def sample_sections():
    """
    Return a simple outline sample: one parent section with one subsection.
    """
    return [
        {
            "title": "Section 1",
            "summary": "Summary 1",
            "subsections": [
                {"title": "Subsection 1-1", "summary": "Sub-summary"}
            ]
        }
    ]

@pytest.fixture
def sample_timeline():
    """
    Return a simple timeline sample: one Phase containing two Tasks,
    initially both marked as completed=True.
    """
    return [
        {
            "title": "Phase 1",
            "start_date": "2025-01-01",
            "end_date":   "2025-01-05",
            "deadline":   "2025-01-04",
            "tasks": [
                {"description": "Task 1", "completed": True},
                {"description": "Task 2", "completed": True},
            ]
        }
    ]

def test_fetch_planning_empty(auth_client):
    """
    GET /planning/ should return empty lists when nothing has been saved.
    """
    resp = auth_client.get("/planning/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["sections"] == []
    assert data["timeline"] == []

def test_save_and_fetch_planning(auth_client, sample_sections, sample_timeline):
    """
    POST /planning/ should save sections and timeline,
    then GET should retrieve them correctly.
    """
    # Save data
    save_resp = auth_client.post(
        "/planning/",
        json={"sections": sample_sections, "timeline": sample_timeline}
    )
    assert save_resp.status_code == 200
    assert save_resp.get_json()["msg"] == "Planning saved"

    # Fetch back
    fetch_resp = auth_client.get("/planning/")
    assert fetch_resp.status_code == 200
    data = fetch_resp.get_json()

    # Verify sections
    assert len(data["sections"]) == len(sample_sections)
    sec = data["sections"][0]
    assert sec["title"] == sample_sections[0]["title"]
    assert sec["summary"] == sample_sections[0]["summary"]
    assert sec["subsections"][0]["title"] == sample_sections[0]["subsections"][0]["title"]

    # Verify timeline
    assert len(data["timeline"]) == len(sample_timeline)
    ph = data["timeline"][0]
    assert ph["title"] == sample_timeline[0]["title"]
    # total_tasks and completed_tasks should match the tasks list length
    assert ph["total_tasks"] == len(sample_timeline[0]["tasks"])
    assert ph["completed_tasks"] == sum(1 for t in sample_timeline[0]["tasks"] if t["completed"])

def test_delete_phase(auth_client, sample_sections, sample_timeline):
    """
    DELETE /planning/<phase_id> should delete the specified phase.
    """
    # First save
    auth_client.post("/planning/", json={"sections": sample_sections, "timeline": sample_timeline})
    data = auth_client.get("/planning/").get_json()
    phase_id = data["timeline"][0]["id"]

    # Delete it
    del_resp = auth_client.delete(f"/planning/{phase_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["msg"] == "Phase deleted"

    # Fetch again, timeline should be empty
    final = auth_client.get("/planning/").get_json()
    assert final["timeline"] == []

@pytest.mark.parametrize("initial_completed, expected_count", [
    (False, 2),  # Flipping from False to True: completed count goes from 1→2
    (True,  1),  # Flipping from True to False: one remains True, completed count goes from 2→1
])
def test_toggle_task(auth_client, sample_sections, sample_timeline,
                     initial_completed, expected_count):
    """
    PATCH /planning/<phase_id>/tasks/<task_id> should toggle the 'completed' field of the given task,
    return JSON with the field flipped, and subsequent GET should reflect the correct completed_tasks count.
    """
    # Adjust the initial completed flag of the first task
    sample_timeline[0]["tasks"][0]["completed"] = initial_completed

    # Save data
    auth_client.post("/planning/", json={
        "sections": sample_sections,
        "timeline": sample_timeline
    })

    # Get phase_id and task_id
    ph = auth_client.get("/planning/").get_json()["timeline"][0]
    phase_id = ph["id"]
    task_id = ph["tasks"][0]["id"]

    # Toggle it
    patch_resp = auth_client.patch(f"/planning/{phase_id}/tasks/{task_id}")
    assert patch_resp.status_code == 200
    toggled = patch_resp.get_json()
    assert toggled["completed"] == (not initial_completed)

    # Fetch again and verify completed_tasks count
    after = auth_client.get("/planning/").get_json()["timeline"][0]
    assert after["completed_tasks"] == expected_count
