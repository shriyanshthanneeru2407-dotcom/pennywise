"""
config.py — PennyWise application configuration.

Uses environment variables for secrets so nothing sensitive is
committed to the repository.
"""

import os
import ssl
from dotenv import load_dotenv

# Load .env file in development (harmless in production)
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def _normalize_db_url(raw_url: str) -> str:
    """Normalize database URL for SQLAlchemy, supporting both psycopg2 and pg8000."""
    if not raw_url:
        return ""
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    
    if not HAS_PSYCOPG2 and raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = raw_url.replace("postgresql://", "postgresql+pg8000://", 1)

    if "pg8000" in raw_url:
        raw_url = raw_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        raw_url = raw_url.replace("?sslmode=disable", "").replace("&sslmode=disable", "")

    return raw_url


def _get_engine_options(db_url: str) -> dict:
    """Build engine options for PostgreSQL / Supabase pooler."""
    options = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    if "pg8000" in db_url:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        options["connect_args"] = {"ssl_context": ctx}
    elif "postgresql" in db_url:
        # For psycopg2 on poolers, keepalives prevent idle disconnects
        options["connect_args"] = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    else:
        return {}
    return options


class Config:
    """Base configuration shared by all environments."""

    # Flask secret key — MUST be set in environment for production
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    _db_url = _normalize_db_url(os.environ.get("DATABASE_URL", ""))
    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'pennywise.db')}"
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options(SQLALCHEMY_DATABASE_URI)
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

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")


class DevelopmentConfig(Config):
    """Development: debug on, SQLite or dev DB, verbose errors."""
    DEBUG = True
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = False  # localhost uses http


class ProductionConfig(Config):
    """Production: no debug, PostgreSQL or serverless SQLite, secure cookies."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Require HTTPS

    _raw_db = _normalize_db_url(os.environ.get("DATABASE_URL", ""))
    SQLALCHEMY_DATABASE_URI = _raw_db or "sqlite:////tmp/pennywise.db"
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options(SQLALCHEMY_DATABASE_URI)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/pennywise_uploads")


class TestingConfig(Config):
    """Testing: in-memory database, no CSRF, isolated uploads."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
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
