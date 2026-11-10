"""
config.py — SpendWise application configuration.

Uses environment variables for secrets so nothing sensitive is
committed to the repository.
"""

import os
from dotenv import load_dotenv

# Load .env file in development (harmless in production)
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # Flask secret key — MUST be set in environment for production
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # SQLAlchemy — default to SQLite for local development
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'spendwise.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload

    # Storage provider: 'local' or 's3'
    STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")
    STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "")
    STORAGE_ACCESS_KEY = os.environ.get("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY = os.environ.get("STORAGE_SECRET_KEY", "")
    STORAGE_ENDPOINT_URL = os.environ.get("STORAGE_ENDPOINT_URL", "")

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # WTF CSRF
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Development: debug on, SQLite, verbose errors."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True to log SQL queries
    SESSION_COOKIE_SECURE = False  # localhost uses http


class ProductionConfig(Config):
    """Production: no debug, PostgreSQL or serverless SQLite, secure cookies."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Require HTTPS

    # Postgres DATABASE_URL from environment or fallback to /tmp on serverless
    _raw_db = os.environ.get("DATABASE_URL", "")
    if _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db or "sqlite:////tmp/spendwise.db"
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/spendwise_uploads")


class TestingConfig(Config):
    """Testing: in-memory database, no CSRF, isolated uploads."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    UPLOAD_FOLDER = "/tmp/spendwise_test_uploads"
    SESSION_COOKIE_SECURE = False


# Map string names to config classes
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
