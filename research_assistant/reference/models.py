from research_assistant.extensions import db
from datetime import datetime

class Reference(db.Model):
    __tablename__ = "reference"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    authors = db.Column(db.String(255), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    source = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Journal related fields
    journal = db.Column(db.String(255))
    volume = db.Column(db.String(50))
    issue = db.Column(db.String(50))
    pages = db.Column(db.String(50))
    doi = db.Column(db.String(255))
    url = db.Column(db.String(255))
    month = db.Column(db.String(20))
    note = db.Column(db.Text)

    completed = db.Column(db.Boolean, default=False)

    tags = db.relationship("Tag", secondary="document_tags", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "source": self.source,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
            "month": self.month,
            "note": self.note,
            "completed": self.completed,
            "tags": [{"id": t.id, "name": t.name} for t in self.tags],
        }
