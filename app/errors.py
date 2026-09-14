"""
app/errors.py — Friendly error page handlers.

Register 404, 403, and 500 error handlers.
In production, these show clean user-friendly pages.
In development, Flask shows detailed tracebacks (DEBUG=True).

IMPORTANT: Never expose stack traces to users in production.
"""

from flask import render_template
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register error handlers with the Flask app."""

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(e):
        # Log the error server-side so developers can debug it
        logger.error(f"Internal server error: {e}")
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, request
        flash("File is too large. Maximum size is 10 MB.", "danger")
        return render_template("errors/413.html"), 413
