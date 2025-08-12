from research_assistant.database import PkModel
from datetime import datetime, timezone
from research_assistant.user.models import User
from research_assistant.extensions import db

class CloudDocument(PkModel):
    """
    Represents a document stored in the cloud.

    Attributes:
        id (int): Primary key, inherited from PkModel.
        title (str): The document's title (required).
        created_at (datetime): Timestamp of when the document was created, defaults to current UTC time.
        versions (list[DocumentVersion]): All versions associated with this document.
    """
    __tablename__ = 'cloud_documents'

    title = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DocumentVersion(PkModel):
    """
    Represents a version of a cloud document.

    Attributes:
        id (int): Primary key, inherited from PkModel.
        document_id (int): Foreign key linking to the parent CloudDocument.
        major_version (int): Major version number (e.g., 1 in v1.0).
        minor_version (int): Minor version number (e.g., 0 in v1.0).
        file_key (str): Key or identifier for the file in the storage provider.
        file_url (str): Public or signed URL to access the stored file.
        storage_provider (str): Name of the storage provider (default: 's3').
        uploaded_by_id (int): Foreign key linking to the User who uploaded the version.
        file_size (float): Size of the uploaded file in bytes or MB.
        uploaded_at (datetime): Timestamp when this version was uploaded, defaults to current UTC time.
        is_current (bool): Flag indicating if this version is the currently active version.
        document (CloudDocument): Relationship to the associated CloudDocument.
        uploader (User): Relationship to the User who uploaded this version.
    """
    __tablename__ = 'document_versions'

    document_id = db.Column(db.Integer, db.ForeignKey('cloud_documents.id'), nullable=False)

    major_version = db.Column(db.Integer, nullable=False, default=1)
    minor_version = db.Column(db.Integer, nullable=False, default=0)

    file_key = db.Column(db.String, nullable=False)
    file_url = db.Column(db.String, nullable=False)
    storage_provider = db.Column(db.String, default='s3')

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_size = db.Column(db.Float)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    is_current = db.Column(db.Boolean, default=True)

    document = db.relationship('CloudDocument', backref='versions')
    uploader = db.relationship('User', backref='uploaded_versions')