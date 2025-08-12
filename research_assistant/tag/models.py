from research_assistant.database import Column, PkModel, db, reference_col, relationship
from research_assistant.reference.models import Reference

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    documents = db.relationship("Reference", secondary="document_tags", back_populates="tags")


# Many-to-many intermediate table, pointing to the reference table instead of the local document table
class DocumentTag(db.Model):
    __tablename__ = "document_tags"

    id = db.Column(db.Integer, primary_key=True)
    document_id = reference_col("reference")  # reference.id
    tag_id = reference_col("tags")
