from datetime import datetime
from research_assistant.extensions import db
from research_assistant.user.models import User

class Section(db.Model):
    __tablename__ = 'sections'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user      = db.relationship('User', backref='sections')

    title     = db.Column(db.String(256), nullable=False)
    summary   = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    parent    = db.relationship('Section', remote_side=[id], backref='subsections')
    order     = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'order': self.order,
            'subsections': [
                s.to_dict() for s in sorted(self.subsections, key=lambda x: x.order)
            ]
        }
