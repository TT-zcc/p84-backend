# -*- coding: utf-8 -*-
"""
Application configuration module.

This file centralizes all Flask application settings.
Most configuration values are loaded from environment variables for flexibility and security.
For local development, use a `.env` file to set environment variables.

Sections:
    - Environment settings
    - Database settings
    - Flask and extension settings
    - Mail configuration
    - JWT authentication
    - AWS S3 storage
"""

import os
from environs import Env

# Initialize environment variable handler
env = Env()
env.read_env()

# =============================
# Environment settings
# =============================
# Application environment (production/development/testing)
ENV = env.str("FLASK_ENV", default="production")
# Enable debug mode if running in development
DEBUG = ENV == "development"

# =============================
# Database configuration
# =============================
# Primary database URL (PostgreSQL/MySQL); defaults to SQLite for local usage
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'sqlite:///data.sqlite'
)
DATABASE_URL = env.str("DATABASE_URL")

# =============================
# Flask core and extension settings
# =============================
# Secret key for Flask sessions and CSRF protection
SECRET_KEY = env.str("SECRET_KEY")
# Maximum age for caching static files
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT", 0)
# Bcrypt hashing rounds for password hashing (higher = more secure but slower)
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
# Enable/disable Flask Debug Toolbar
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
# Simple in-memory cache for development
CACHE_TYPE = "flask_caching.backends.SimpleCache"
# Disable SQLAlchemy event system to reduce overhead
SQLALCHEMY_TRACK_MODIFICATIONS = False
# Disable CSRF globally (enable in production if required)
WTF_CSRF_ENABLED = False

# =============================
# Mail server configuration
# =============================
# SMTP server details
MAIL_SERVER = env.str("MAIL_SERVER")
MAIL_PORT = env.int("MAIL_PORT")
MAIL_USE_TLS = env.bool("MAIL_USE_TLS", False)
MAIL_USERNAME = env.str("MAIL_USERNAME")
MAIL_PASSWORD = env.str("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = env.str("MAIL_USERNAME")

# =============================
# JWT (JSON Web Token) configuration
# =============================
# Secret key used to sign JWT tokens
JWT_SECRET_KEY = env.str("JWT_SECRET_KEY")
# Access token expiration time in seconds (24 hours by default)
JWT_ACCESS_TOKEN_EXPIRES = 86400

# =============================
# AWS S3 configuration
# =============================
# AWS credentials for S3 operations
AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
# S3 bucket details
AWS_S3_BUCKET_NAME = env.str("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = env.str("AWS_S3_REGION")
# Preconfigured endpoint URL for accessing S3 bucket
AWS_S3_ENDPOINT_URL = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com"
