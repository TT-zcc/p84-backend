import pytest
from datetime import timedelta, date
from research_assistant.planning.models import Phase, Task
from research_assistant.extensions import db


def create_phase(user_id, title, tasks=None, deadline=None):
    """
    Helper: Create a research phase along with its tasks.

    Args:
        user_id (int): The ID of the user who owns the phase.
        title (str): Title of the phase.
        tasks (list[dict], optional): A list of dictionaries representing tasks. 
            Each dictionary must include at least:
                - description (str)
                - completed (bool)
            Defaults to one task: {"description": "Default Task", "completed": False}.
        deadline (date, optional): Optional deadline for the phase.

    Returns:
        Phase: The created Phase instance.
    """
    phase = Phase(title=title, user_id=user_id, deadline=deadline)
    if tasks is None:
        tasks = [{"description": "Default Task", "completed": False}]
    for t in tasks:
        task = Task(
            description=t.get("description", "No description"),
            completed=t.get("completed", False),
            user_id=user_id
        )
        phase.tasks.append(task)
    db.session.add(phase)
    db.session.commit()
    return phase


def get_phase_data(auth_client, title):
    """
    Helper: Fetch a specific phase's data from the API response.

    Args:
        auth_client: Authenticated test client instance.
        title (str): Title of the phase to retrieve.

    Returns:
        dict: The JSON data for the matching phase.
    """
    res = auth_client.get("/dashboard/phases")
    assert res.status_code == 200
    data = res.get_json()["data"]
    return next(p for p in data if p["title"] == title)


def test_fetch_phases_all_completed(auth_client, test_user):
    """Verify that a phase with all tasks completed is marked as 'Completed'."""
    create_phase(test_user.id, "Define Topic & Question", tasks=[{"description": "Task1", "completed": True}])
    phase_data = get_phase_data(auth_client, "Define Topic & Question")
    assert phase_data["status"] == "Completed"


def test_fetch_phases_not_completed(auth_client, test_user):
    """Verify that a phase with incomplete tasks is marked as 'NotCompleted'."""
    create_phase(test_user.id, "Literature Review", tasks=[{"description": "Task1", "completed": False}])
    phase_data = get_phase_data(auth_client, "Literature Review")
    assert phase_data["status"] == "NotCompleted"


def test_deadline_approaching(auth_client, test_user):
    """Verify that a phase close to its deadline is marked as 'Deadline Approaching'."""
    deadline = date.today() + timedelta(days=3)
    create_phase(
        test_user.id,
        "Identify Gaps",
        tasks=[{"description": "Task1", "completed": False}],
        deadline=deadline
    )
    phase_data = get_phase_data(auth_client, "Identify Gaps")
    assert "Deadline Approaching" in phase_data["status"]


def test_deadline_overdue(auth_client, test_user):
    """Verify that a phase past its deadline is marked as 'Overdue'."""
    deadline = date.today() - timedelta(days=1)
    create_phase(
        test_user.id,
        "Plan Methodology",
        tasks=[{"description": "Task1", "completed": False}],
        deadline=deadline
    )
    phase_data = get_phase_data(auth_client, "Plan Methodology")
    assert "Overdue" in phase_data["status"]


def test_missing_phase_defaults_to_not_completed(auth_client):
    """Verify that a missing phase defaults to 'NotCompleted' status."""
    res = auth_client.get("/dashboard/phases")
    assert res.status_code == 200
    data = res.get_json()["data"]
    titles = [p["title"] for p in data]
    assert "Write & Revise" in titles
    phase_data = next(p for p in data if p["title"] == "Write & Revise")
    assert phase_data["status"] == "NotCompleted"


def test_unauthorized_access(client):
    """Verify that accessing phases without authentication returns 401."""
    res = client.get("/dashboard/phases")
    assert res.status_code == 401


def test_phase_with_no_tasks(auth_client, test_user):
    """Verify that a phase with no tasks is marked as 'NotCompleted'."""
    phase = Phase(title="Define Topic & Question", user_id=test_user.id)
    db.session.add(phase)
    db.session.commit()
    phase_data = get_phase_data(auth_client, "Define Topic & Question")
    assert phase_data["status"] == "NotCompleted"


def test_phase_partial_tasks_completed(auth_client, test_user):
    """Verify that a phase with partially completed tasks is marked as 'NotCompleted'."""
    create_phase(
        test_user.id,
        "Literature Review",
        tasks=[
            {"description": "T1", "completed": True},
            {"description": "T2", "completed": False}
        ]
    )
    phase_data = get_phase_data(auth_client, "Literature Review")
    assert phase_data["status"] == "NotCompleted"
