# -*- coding: utf-8 -*-
"""
App module.

This module defines the Flask application factory and supporting
functions for initializing the app, registering blueprints, extensions,
error handlers, and loggers.

Usage:
    - In production, import and call `create_app()`.
    - For local development, this script can be run directly:
        python app.py
"""

import logging
import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect
from flask_migrate import upgrade as migrate_upgrade
from research_assistant import settings

from research_assistant import public, user
from research_assistant.ai_assistant.views import blueprint as ai_bp
from research_assistant.brain.views import brainstorm_bp
from research_assistant.chat.views import chat_bp
from research_assistant.dashboard.views import dashboard as dashboard_blueprint
from research_assistant.outline.views import outline_bp
from research_assistant.planning.views import planning_bp
from research_assistant.tag.views import blueprint as tag_bp
from research_assistant.writing_tool.routes import writing_tool_bp
from research_assistant.reference.models import Reference
from research_assistant.reference.views import bp as reference_bp
from research_assistant.user_settings.views import settings_bp
from research_assistant.extensions import (
    bcrypt,
    cache,
    csrf_protect,
    db,
    debug_toolbar,
    flask_static_digest,
    init_s3_client,
    jwt,
    login_manager,
    mail,
    migrate,
)


def create_app(config_object="research_assistant.settings"):
    """
    Application factory function.

    Initializes the Flask application with:
        - Configuration from the provided config object
        - Database connection
        - JWT, Mail, and AWS S3 clients
        - CSRF protection
        - Blueprints for modular routes
        - Error handlers and shell context

    Args:
        config_object (str): Python path to the configuration object.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    # Enable CORS for frontend communication
    CORS(app, origins=[settings.env.str("CORS_ORIGIN", "http://localhost:5173")], supports_credentials=True)

    # Override database URI if DATABASE_URL is set in the environment
    if settings.env.str("DATABASE_URL", None):
        app.config["SQLALCHEMY_DATABASE_URI"] = settings.env.str("DATABASE_URL")

    # Initialize extensions
    register_extensions(app)

    # Register Writing Tool blueprint and exempt from CSRF
    app.register_blueprint(writing_tool_bp, url_prefix="/writing_tool")
    csrf_protect.exempt(writing_tool_bp)

    # Register Public blueprint and exempt from CSRF
    app.register_blueprint(public.views.blueprint)
    csrf_protect.exempt(public.views.blueprint)

    # Initialize mail and AWS S3 client
    mail.init_app(app)
    init_s3_client(app)
    app.config["PROPAGATE_EXCEPTIONS"] = True

    # Attempt to create tables on startup if needed (non-blocking)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(
                "Skipping table inspection on startup; will create_all later if needed",
                exc_info=e,
            )

    # Register other blueprints, error handlers, shell context
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    configure_logger(app)

    return app


def register_extensions(app):
    """
    Register Flask extensions with the application.

    Extensions include:
        - Bcrypt for password hashing
        - Cache for performance
        - SQLAlchemy ORM
        - CSRF protection
        - Login Manager for user session handling
        - Debug toolbar for development
        - Database migrations
        - Static digest for cache busting
        - JWT for authentication
    """
    bcrypt.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    csrf_protect.init_app(app)
    login_manager.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    flask_static_digest.init_app(app)
    jwt.init_app(app)
    return None


def register_blueprints(app):
    """
    Register additional Flask blueprints for modular route handling.
    """
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(dashboard_blueprint)
    app.register_blueprint(tag_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(brainstorm_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(outline_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(reference_bp)
    app.register_blueprint(settings_bp)
    return None


def register_errorhandlers(app):
    """
    Register JSON error handlers for common HTTP error codes (401, 404, 500).

    Returns JSON responses instead of HTML error pages.
    """
    def render_error(error):
        code = getattr(error, "code", 500)
        desc = getattr(error, "description", "Server Error")
        return jsonify({"code": code, "msg": desc}), code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """
    Register shell context objects for interactive `flask shell`.

    Allows quick access to database and models.
    """
    def shell_context():
        return {"db": db, "User": user.models.User}
    app.shell_context_processor(shell_context)

def configure_logger(app):
    """
    Configure the Flask app logger to write to stdout.

    Ensures that logs are captured properly in containerized
    environments like Docker or cloud platforms.
    """
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)


# Main entrypoint for local development
# In production, the application factory is used by WSGI servers
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))  # nosec B104
