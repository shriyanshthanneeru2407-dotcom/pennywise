"""
app/settings/routes.py — User profile, preferences, and account management.

Routes:
  GET  /settings         → Profile/settings page
  POST /settings/profile → Update name, email, date format
  POST /settings/password → Change password
  POST /settings/preferences → Update currency, theme
  GET  /export/expenses.csv → Download CSV export
  POST /settings/delete-account → Delete account (with confirmation)
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user, logout_user
from app import db
from app.models.user import User
from app.services.export_service import generate_expenses_csv

settings_bp = Blueprint("settings", __name__)

SUPPORTED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "AED", "SGD", "CHF"]
SUPPORTED_THEMES = ["light", "dark"]
DATE_FORMATS = ["%d %b %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


def _is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


@settings_bp.route("/")
@settings_bp.route("")
@login_required
def index():
    return render_template(
        "settings/index.html",
        currencies=SUPPORTED_CURRENCIES,
        themes=SUPPORTED_THEMES,
        date_formats=DATE_FORMATS,
    )


@settings_bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    date_format = request.form.get("date_format", "%d %b %Y")

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or not _is_valid_email(email):
        errors.append("A valid email address is required.")
    if date_format not in DATE_FORMATS:
        date_format = "%d %b %Y"

    # Check email uniqueness (excluding self)
    if email and email != current_user.email:
        existing = User.query.filter_by(email=email).first()
        if existing:
            errors.append("That email address is already in use.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return redirect(url_for("settings.index"))

    current_user.name = name
    current_user.email = email
    current_user.date_format = date_format
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/password", methods=["POST"])
@login_required
def update_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("settings.index"))

    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "danger")
        return redirect(url_for("settings.index"))

    if new_password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("settings.index"))

    current_user.set_password(new_password)
    db.session.commit()
    flash("Password updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/preferences", methods=["POST"])
@login_required
def update_preferences():
    currency = request.form.get("currency", "INR")
    theme = request.form.get("theme", "light")

    if currency not in SUPPORTED_CURRENCIES:
        currency = "INR"
    if theme not in SUPPORTED_THEMES:
        theme = "light"

    current_user.currency = currency
    current_user.theme = theme
    db.session.commit()
    flash("Preferences updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/export/expenses.csv")
@login_required
def export_expenses():
    """Generate and download a CSV of the user's expenses."""
    csv_content = generate_expenses_csv(current_user.id)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=pennywise-transactions.csv"
        },
    )


@settings_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    """
    Permanently delete the user account.
    Requires typing 'DELETE' as confirmation to prevent accidental deletion.
    Cascade foreign keys ensure all expenses/budgets/etc. are removed.
    This is a POST-only route (never GET) for CSRF protection.
    """
    confirm = request.form.get("confirm_text", "").strip()

    if confirm != "DELETE":
        flash("Please type DELETE to confirm account deletion.", "danger")
        return redirect(url_for("settings.index"))

    user = current_user._get_current_object()
    logout_user()

    db.session.delete(user)
    db.session.commit()

    flash("Your account has been permanently deleted.", "info")
    return redirect(url_for("main.index"))
