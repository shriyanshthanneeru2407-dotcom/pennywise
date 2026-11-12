import os
import sys
import logging

# Ensure root directory is on Python path so 'app' package is found
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app

try:
    app = create_app(os.environ.get("FLASK_ENV", "production"))
except Exception as exc:
    logging.error(f"Failed to start with default database: {exc}. Falling back to /tmp sqlite.")
    # Fallback to local /tmp sqlite if remote database connection encounters network issues
    os.environ["DATABASE_URL"] = "sqlite:////tmp/spendwise.db"
    app = create_app("production")
