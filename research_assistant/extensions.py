# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
import boto3
from flask import current_app
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_static_digest import FlaskStaticDigest
from flask_wtf.csrf import CSRFProtect

# Core extensions
bcrypt = Bcrypt()
csrf_protect = CSRFProtect()
login_manager = LoginManager()
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
debug_toolbar = DebugToolbarExtension()
flask_static_digest = FlaskStaticDigest()
mail = Mail()
jwt = JWTManager()

# User model import for the user_loader
from research_assistant.user.models import User  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    """Load the user by ID for Flask-Login."""
    return User.query.get(int(user_id))

# Return JSON 401 instead of redirect when unauthorized
login_manager.unauthorized_handler(lambda: ("Unauthorized", 401))

def init_s3_client(app):
    """
    Initialize an S3 client attached to the Flask app instance.
    Credentials and region come from app.config.
    """
    app.s3_client = boto3.client(
        "s3",
        aws_access_key_id=app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=app.config["AWS_SECRET_ACCESS_KEY"],
        region_name=app.config.get("AWS_S3_REGION"),
    )

def get_s3_client():
    """Retrieve the initialized S3 client from the current app context."""
    return current_app.s3_client
