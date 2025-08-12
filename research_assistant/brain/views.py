from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from research_assistant.brain.models import BrainEntry
from research_assistant.extensions import db
from research_assistant.planning.models import Phase, Task
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

brainstorm_bp = Blueprint('brainstorm', __name__, url_prefix='/brainstorm')

@brainstorm_bp.route('/load', methods=['GET'])
@jwt_required()
def load_brainstorm_session():
    """Load the latest brainstorm session for the logged-in user."""
    user_id = get_jwt_identity()
    entry = (
        BrainEntry.query
        .filter_by(user_id=user_id)
        .order_by(BrainEntry.updated_at.desc())
        .first()
    )
    if entry:
        return jsonify(entry.to_dict()), 200
    else:
        return jsonify({}), 200


@brainstorm_bp.route('/save', methods=['POST'])
@jwt_required()
def save_brainstorm_session():
    """Save a new brainstorm session entry with 5W, chat, feedback, and status."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    fiveW = data.get('fiveW', {})
    messages = data.get('messages', [])
    overall_feedback = data.get('overallFeedback', '')
    completed = data.get('completed', False)

    entry = BrainEntry(
        why=fiveW.get('why'),
        what=fiveW.get('what'),
        where=fiveW.get('where'),
        when=fiveW.get('when'),
        who=fiveW.get('who'),
        messages=json.dumps(messages),
        overall_feedback=overall_feedback,
        completed=completed,
        user_id=user_id,
    )

    db.session.add(entry)

    if all([entry.why, entry.what, entry.where, entry.when, entry.who]):
        phase = Phase.query.filter_by(title='Define Topic & Question').first()
        if phase and not any(t.description == 'Brainstorm Complete' for t in phase.tasks):
            new_task = Task(
                user_id=user_id,
                description='Brainstorm Complete',
                completed=True
            )
            phase.tasks.append(new_task)
            db.session.add(new_task)

    db.session.commit()
    return jsonify({'id': entry.id}), 201


@brainstorm_bp.route('/progress', methods=['POST'])
@jwt_required()
def complete_brainstorm_step():
    """
    Update brainstorm step completion status for the current user.
    """
    # Get current user ID
    user_id = get_jwt_identity()

    # Read request JSON and get 'completed' flag
    data = request.get_json() or {}
    completed_flag = data.get("completed", False)

    # Get the latest brainstorm entry for the user
    entry = (
        BrainEntry.query
        .filter_by(user_id=user_id)
        .order_by(BrainEntry.updated_at.desc())
        .first()
    )

    # If no entry found
    if not entry:
        return jsonify({"error": "No brainstorm entry found"}), 404

    # Update and save completion status
    entry.completed = completed_flag
    db.session.commit()

    # Respond with updated status
    return jsonify({"status": "ok", "completed": entry.completed}), 200
