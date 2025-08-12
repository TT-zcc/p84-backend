# research_assistant/planning/views.py
from datetime import date
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from research_assistant.extensions import db
from research_assistant.outline.models import Section
from research_assistant.planning.models import Phase, Task

planning_bp = Blueprint('planning', __name__, url_prefix='/planning')

@planning_bp.route('/', methods=['GET'])
@jwt_required()
def fetch_planning():
    uid = get_jwt_identity()

    sections = (
        Section.query
        .filter_by(parent_id=None, user_id=uid)
        .order_by(Section.order)
        .all()
    )
    sections_json = [sec.to_dict() for sec in sections]

    phases = (
        Phase.query
        .filter_by(user_id=uid)
        .order_by(Phase.order)
        .all()
    )
    timeline_json = [ph.to_dict() for ph in phases]

    return jsonify({
        'sections': sections_json,
        'timeline': timeline_json
    }), 200


@planning_bp.route('/', methods=['POST'])
@jwt_required()
def save_planning():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    sections_data = data.get('sections', [])
    timeline_data = data.get('timeline', [])

    Section.query.filter_by(user_id=uid).delete()
    db.session.commit()

    def _create_sections(items, parent_id=None):
        for idx, item in enumerate(items):
            sec = Section(
                title     = item.get('title'),
                summary   = item.get('summary'),
                parent_id = parent_id,
                order     = idx,
                user_id   = uid,
            )
            db.session.add(sec)
            db.session.flush()
            _create_sections(item.get('subsections', []), sec.id)

    _create_sections(sections_data)
    db.session.commit()

    Task.query.filter_by(user_id=uid).delete()
    Phase.query.filter_by(user_id=uid).delete()
    db.session.commit()

    for idx, ph_item in enumerate(timeline_data):
        ph = Phase(
            title      = ph_item.get('title'),
            start_date = date.fromisoformat(ph_item['start_date']) if ph_item.get('start_date') else None,
            end_date   = date.fromisoformat(ph_item['end_date'])   if ph_item.get('end_date')   else None,
            deadline   = date.fromisoformat(ph_item['deadline'])   if ph_item.get('deadline')   else None,
            order      = idx,
            user_id    = uid,
        )
        for task_item in ph_item.get('tasks', []):
            t = Task(
                description = task_item.get('description'),
                completed   = bool(task_item.get('completed', False)),
                user_id     = uid,
            )
            ph.tasks.append(t)

        db.session.add(ph)

    db.session.commit()
    return jsonify({'msg': 'Planning saved'}), 200


@planning_bp.route('/<int:phase_id>', methods=['DELETE'])
@jwt_required()
def delete_phase(phase_id):
    uid = get_jwt_identity()
    phase = Phase.query.filter_by(id=phase_id, user_id=uid).first_or_404()
    db.session.delete(phase)
    db.session.commit()
    return jsonify({'msg': 'Phase deleted'}), 200


@planning_bp.route('/<int:phase_id>/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required()
def toggle_task(phase_id, task_id):
    uid = get_jwt_identity()
    task = Task.query.filter_by(
        id=task_id, phase_id=phase_id, user_id=uid
    ).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return jsonify(task.to_dict()), 200
