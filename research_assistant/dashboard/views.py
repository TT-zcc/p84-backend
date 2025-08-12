# research_assistant/dashboard/views.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from research_assistant.planning.models import Phase
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Define a blueprint for dashboard-related routes
# This allows grouping of endpoints under the '/dashboard' URL prefix
dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard.route("/phases", methods=["GET"])
@jwt_required()
def fetch_planning():
    """
    Retrieve all research planning phases for the currently authenticated user.

    This endpoint returns the list of predefined research phases in a fixed order
    and determines their completion status based on associated tasks and deadlines.

    Statuses include:
        - "Completed": All tasks within the phase are completed.
        - "NotCompleted": At least one task is incomplete.
        - "Not Completed (Deadline Approaching)": At least one task is incomplete and 
          the deadline is within 7 days.
        - "Not Completed (Overdue)": The phase's deadline has passed without completion.

    Authentication:
        - Requires a valid JWT token to identify the current user.

    Returns:
        JSON:
            {
                "code": 0,
                "data": [
                    {
                        "id": <int>,          # Sequential phase identifier
                        "title": <string>,    # Phase title
                        "status": <string>    # Completion status
                    },
                    ...
                ]
            }
    """
    # Get the user ID from the JWT token
    uid = get_jwt_identity()

    # Fetch all phases associated with the current user
    user_phases = Phase.query.filter_by(user_id=uid).all()

    # Map phase titles to Phase objects for quick lookup
    user_phase_map = {p.title: p for p in user_phases}

    # Define the standard order in which phases should be displayed
    desired_order = [
        'Define Topic & Question',
        'Literature Review',
        'Identify Gaps',
        'Plan Methodology',
        'Write & Revise'
    ]

    # Time threshold for approaching deadlines
    warning_threshold = timedelta(days=7)

    # Current timestamp for deadline comparison
    local_tz = ZoneInfo("Australia/Sydney")
    now = datetime.now(local_tz)

    # Container for final output data
    data = []

    for index, title in enumerate(desired_order):
        # Retrieve the phase object if it exists for the user
        phase = user_phase_map.get(title)

        if phase:
            tasks = phase.tasks

            # Default status
            status = "NotCompleted"

            # If all tasks are completed, mark as completed
            if tasks and all(t.completed for t in tasks):
                status = "Completed"
            else:
                # Check for deadline-related warnings
                if phase.deadline:
                    deadline_dt = datetime.combine(phase.deadline, datetime.max.time()).replace(tzinfo=local_tz)

                    if deadline_dt < now:
                        status = "Not Completed (Overdue)"
                    elif (deadline_dt - now) <= warning_threshold:
                        status = "Not Completed (Deadline Approaching)"
            data.append({
                "id": index + 1,     # Sequential ID based on the fixed order
                "title": phase.title,
                "status": status,
            })
        else:
            # If the phase is not created by the user, consider it incomplete
            data.append({
                "id": index + 1,
                "title": title,
                "status": "NotCompleted"
            })

    # Return standardized JSON response
    return jsonify({
        "code": 0,
        "data": data
    }), 200
