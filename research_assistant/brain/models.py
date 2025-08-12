from datetime import datetime
from research_assistant.extensions import db
from research_assistant.user.models import User
import json

class BrainEntry(db.Model):
    __tablename__ = 'brain_entries'

    id = db.Column(db.Integer, primary_key=True)
    why = db.Column(db.String(512))
    what = db.Column(db.String(512))
    where = db.Column(db.String(512))
    when = db.Column(db.String(128))
    who = db.Column(db.String(256))
    messages = db.Column(db.Text)  # Store message history as JSON string
    overall_feedback = db.Column(db.Text)  # Store overall AI feedback
    completed = db.Column(db.Boolean, default=False)  # Whether the step is marked complete

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='brain_entries')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Return dictionary with nested fiveW object to match frontend expectations."""
        return {
            'id': self.id,
            'fiveW': {
                'why': self.why,
                'what': self.what,
                'where': self.where,
                'when': self.when,
                'who': self.who,
            },
            'messages': json.loads(self.messages) if self.messages else [],
            'overallFeedback': self.overall_feedback,
            'completed': self.completed,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
