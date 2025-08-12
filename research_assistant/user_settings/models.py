from research_assistant.extensions import db
from research_assistant.user.models import User

class UserSettings(db.Model):
    __tablename__ = "user_settings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False)
    language = db.Column(db.String(20), default="en")
    theme = db.Column(db.String(20), default="light")
    notifications_enabled = db.Column(db.Boolean, default=True)
    export_format = db.Column(db.String(10), default="pdf")

    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            "name": user.username if user else "",
            "email": user.email if user else "",
            "language": self.language,
            "theme": self.theme,
            "notifications_enabled": self.notifications_enabled,
            "export_format": self.export_format,
        }
