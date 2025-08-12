# research_assistant/planning/models.py

from datetime import date, datetime
from research_assistant.extensions import db
from research_assistant.user.models import User  # import User

class Phase(db.Model):
    __tablename__ = 'phases'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user       = db.relationship('User', backref='phases')

    title      = db.Column(db.String(256), nullable=False)
    order      = db.Column(db.Integer, nullable=False, default=0)
    start_date = db.Column(db.Date)
    end_date   = db.Column(db.Date)
    deadline   = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = db.relationship(
        'Task',
        backref='phase',
        cascade='all, delete-orphan',
        order_by='Task.id'
    )

    def to_dict(self):
        # compute task progress
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for t in self.tasks if t.completed)
        pct_complete = (completed_tasks / total_tasks * 100) if total_tasks else 0

        today = date.today()
        days_left = (self.deadline - today).days if self.deadline else None
        status = 'Completed' if pct_complete == 100 else 'OnTrack'

        return {
            'id':              self.id,
            'title':           self.title,
            'order':           self.order,
            'start_date':      self.start_date.isoformat() if self.start_date else None,
            'end_date':        self.end_date.isoformat()   if self.end_date   else None,
            'deadline':        self.deadline.isoformat()   if self.deadline   else None,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
            'updated_at':      self.updated_at.isoformat() if self.updated_at else None,
            'total_tasks':     total_tasks,
            'completed_tasks': completed_tasks,
            'pct_complete':    round(pct_complete, 1),
            'days_left':       days_left,
            'status':          status,
            'tasks':           [t.to_dict() for t in self.tasks],
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user        = db.relationship('User', backref='tasks')

    description = db.Column(db.String(512), nullable=False)
    completed   = db.Column(db.Boolean, default=False)
    phase_id    = db.Column(db.Integer, db.ForeignKey('phases.id'))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'description': self.description,
            'completed':   self.completed,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
            'updated_at':  self.updated_at.isoformat() if self.updated_at else None,
        }
