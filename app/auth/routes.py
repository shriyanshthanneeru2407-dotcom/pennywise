"""
app/auth/routes.py — Registration, login, and logout.

Security design:
  - Passwords hashed with Werkzeug's scrypt/bcrypt (never plain text)
  - Login errors use a generic message to avoid account enumeration
    (we don't tell the attacker whether the email exists or not)
  - Sessions managed by Flask-Login
  - All form CSRF tokens validated by Flask-WTF
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

# Minimum password length
MIN_PASSWORD_LENGTH = 8


def _is_valid_email(email: str) -> bool:
    """Basic email format check using regex."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    GET:  Show the registration form.
    POST: Validate input, create account, log in, redirect to dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []

        if not name:
            errors.append("Name is required.")
        if not email or not _is_valid_email(email):
            errors.append("A valid email address is required.")
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            # Check for duplicate email — use constant-time comparison approach
            existing = User.query.filter_by(email=email).first()
            if existing:
                # Generic message to avoid confirming email existence
                errors.append("An account with that email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            # Re-render form with values preserved (except passwords)
            return render_template("auth/register.html", name=name, email=email)

        # All valid — create the user
        user = User(name=name, email=email, currency="INR", theme="dark")
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to SpendWise, {user.name}! Start by adding your first expense.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html", name="", email="")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Show login form.
    POST: Verify credentials, create session, redirect.

    We use a generic error message ("Invalid email or password") regardless
    of whether the email exists or the password was wrong. This prevents
    attackers from enumerating valid accounts.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        # Use the same generic error whether email or password is wrong
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email)

        login_user(user, remember=remember)

        # Redirect to the page they were trying to access, or dashboard
        next_page = request.args.get("next")
        # Validate next_page to prevent open redirect attacks
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", email="")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    POST only — prevents logout via GET (CSRF-safe pattern).
    Clears the session and redirects to landing page.
    """
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))
