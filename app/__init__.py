"""
app/__init__.py — Application factory.

Using the factory pattern (create_app) lets us:
  1. Create the app with different configs (dev vs prod vs testing)
  2. Avoid circular imports between models and routes
  3. Easily spin up multiple app instances in tests
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Core extensions — initialized here, bound to app in create_app()
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()


def create_app(config_name: str = None) -> Flask:
    """
    Application factory.

    Args:
        config_name: 'development', 'production', or None (uses FLASK_ENV env var)

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Load configuration ---
    from config import config as config_map

    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["default"]))

    # Ensure the instance folder exists (for SQLite + local uploads)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "instance/uploads"), exist_ok=True)

    # --- Bind extensions to app ---
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"          # Where to redirect unauthenticated users
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"

    # --- Register blueprints ---
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.expenses.routes import expenses_bp
    from app.budgets.routes import budgets_bp
    from app.recurring.routes import recurring_bp
    from app.insights.routes import insights_bp
    from app.settings.routes import settings_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(budgets_bp, url_prefix="/budget")
    app.register_blueprint(recurring_bp, url_prefix="/recurring")
    app.register_blueprint(insights_bp, url_prefix="/insights")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    # --- Register error handlers ---
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # --- Import models so Flask-Migrate can detect them ---
    from app.models import user, expense, category, budget, recurring, receipt  # noqa: F401

    return app
