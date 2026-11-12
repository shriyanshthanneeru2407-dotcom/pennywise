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

    # Ensure the instance and upload folders exist (safely catch Read-only filesystem on serverless)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    try:
        os.makedirs(app.config.get("UPLOAD_FOLDER", "/tmp/spendwise_uploads"), exist_ok=True)
    except OSError:
        pass

    # Support reverse proxies (Vercel, AWS, etc.) for correct HTTPS, proto, and host detection
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
    from app.savings.routes import savings_bp
    from app.insights.routes import insights_bp
    from app.reports.routes import reports_bp
    from app.settings.routes import settings_bp
    from app.notifications.routes import notifications_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(budgets_bp, url_prefix="/budget")
    app.register_blueprint(savings_bp, url_prefix="/savings")
    app.register_blueprint(recurring_bp, url_prefix="/recurring")
    app.register_blueprint(insights_bp, url_prefix="/insights")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        from app.models.notification import Notification
        try:
            if current_user and current_user.is_authenticated:
                count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
                return {"unread_notifications_count": count}
        except Exception:
            pass
        return {"unread_notifications_count": 0}

    # --- Register error handlers ---
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # --- Import models so Flask-Migrate can detect them ---
    from app.models import user, expense, category, budget, recurring, receipt, savings, notification  # noqa: F401

    # Ensure tables and default data exist (immediate for SQLite/testing; PostgreSQL tables are pre-created)
    with app.app_context():
        try:
            if db.engine.dialect.name == "sqlite":
                db.create_all()

                # Seed system categories if none exist
                from app.models.category import Category, DEFAULT_CATEGORIES
                try:
                    if not Category.query.filter_by(user_id=None).first():
                        for cat_data in DEFAULT_CATEGORIES:
                            db.session.add(Category(user_id=None, **cat_data))
                        db.session.commit()
                except Exception:
                    db.session.rollback()

                # Seed demo user if none exists
                from app.models.user import User
                try:
                    if not User.query.filter_by(email="demo@pennywise.app").first():
                        demo_user = User(
                            name="PennyWise Demo",
                            email="demo@pennywise.app",
                            currency="INR",
                            theme="dark",
                        )
                        demo_user.set_password("demo1234")
                        db.session.add(demo_user)
                        db.session.commit()
                except Exception:
                    db.session.rollback()
        except Exception as e:
            app.logger.warning(f"Database setup deferred or connection not ready: {e}")

    return app
