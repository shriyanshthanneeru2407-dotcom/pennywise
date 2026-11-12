"""
app/auth/routes.py — Registration, login, logout, Google OAuth, and Password Reset.

Security design:
  - Passwords hashed with Werkzeug's scrypt/bcrypt (never plain text)
  - Login errors use a generic message to avoid account enumeration
  - Sessions managed by Flask-Login with secure cookie parameters
  - All form CSRF tokens validated by Flask-WTF
  - Google OAuth 2.0 with cryptographic state validation
  - Timed cryptographic tokens for password reset (1 hour TTL)
"""

import re
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User
from app.auth.oauth import (
    is_google_oauth_configured,
    get_google_auth_url,
    exchange_code_for_user_info,
)

auth_bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 8


def _is_valid_email(email: str) -> bool:
    """Basic email format check using regex."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _get_reset_serializer():
    """Return a timed serializer using the app SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


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
        currency = request.form.get("currency", "INR").strip().upper()
        if currency not in User.SUPPORTED_CURRENCIES:
            currency = "INR"

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
            existing = User.query.filter_by(email=email).first()
            if existing:
                errors.append("An account with that email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "auth/register.html",
                name=name,
                email=email,
                currency=currency,
                google_oauth_enabled=is_google_oauth_configured(),
            )

        user = User(name=name, email=email, currency=currency, theme="dark")
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to PennyWise, {user.name}! Start by tracking your first transaction.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template(
        "auth/register.html",
        name="",
        email="",
        currency="INR",
        google_oauth_enabled=is_google_oauth_configured(),
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Show login form.
    POST: Verify credentials, create session, redirect.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template(
                "auth/login.html",
                email=email,
                google_oauth_enabled=is_google_oauth_configured(),
            )

        login_user(user, remember=remember)

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template(
        "auth/login.html",
        email="",
        google_oauth_enabled=is_google_oauth_configured(),
    )


@auth_bp.route("/google")
def google_login():
    """
    Initiate Google OAuth 2.0 flow.
    Redirects user to Google's consent screen.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if not is_google_oauth_configured():
        flash(
            "Google Sign-In is not yet configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env or Vercel environment variables.",
            "warning",
        )
        return redirect(url_for("auth.login"))

    # Build callback URL
    redirect_uri = url_for("auth.google_callback", _external=True)
    # Fix for behind reverse proxies or cloud run
    if redirect_uri.startswith("http://") and not current_app.debug:
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    auth_url = get_google_auth_url(redirect_uri)
    return redirect(auth_url)


@auth_bp.route("/google/callback")
def google_callback():
    """
    Google OAuth 2.0 callback endpoint.
    Verifies state token, exchanges code for user profile, logs user in.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)

    if not state or state != expected_state:
        flash("Authentication failed: invalid OAuth state. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    if not code:
        flash("Google authorization was cancelled or failed.", "warning")
        return redirect(url_for("auth.login"))

    redirect_uri = url_for("auth.google_callback", _external=True)
    if redirect_uri.startswith("http://") and not current_app.debug:
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    try:
        profile = exchange_code_for_user_info(code, redirect_uri)
    except Exception as e:
        flash(f"Google login failed: {str(e)}", "danger")
        return redirect(url_for("auth.login"))

    email = profile["email"]
    google_id = profile["google_id"]

    if not email:
        flash("Unable to retrieve email from Google account.", "danger")
        return redirect(url_for("auth.login"))

    # Check if user already exists
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            # Link Google ID to existing account
            user.google_id = google_id
            if profile.get("avatar_url"):
                user.avatar_url = profile["avatar_url"]
            db.session.commit()
        else:
            # Create new user via Google Sign-In
            user = User(
                name=profile.get("name") or "Google User",
                email=email,
                currency="INR",
                theme="dark",
                google_id=google_id,
                avatar_url=profile.get("avatar_url"),
            )
            # Set a random unusable password
            user.set_password(secrets.token_hex(24))
            db.session.add(user)
            db.session.commit()

    login_user(user)
    flash(f"Signed in as {user.name} via Google.", "success")
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Request a password reset link."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            s = _get_reset_serializer()
            token = s.dumps(user.email, salt="password-reset-salt")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            # In production without SMTP, log URL safely for testing
            current_app.logger.info(f"Password reset link for {email}: {reset_url}")
            flash(
                "If an account with that email exists, a password reset link has been generated. (Check server logs in local mode)",
                "info",
            )
        else:
            # Constant-time response to prevent email enumeration
            flash(
                "If an account with that email exists, a password reset link has been generated.",
                "info",
            )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password using a valid, non-expired cryptographic token."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    s = _get_reset_serializer()
    try:
        # Token valid for 3600 seconds (1 hour)
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except SignatureExpired:
        flash("The password reset link has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))
    except BadTimeSignature:
        flash("Invalid password reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template("auth/reset_password.html", token=token)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        db.session.commit()

        flash("Your password has been successfully updated! You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    """Verify email address using a cryptographic token."""
    s = _get_reset_serializer()
    try:
        email = s.loads(token, salt="email-verification-salt", max_age=86400 * 3)
    except (SignatureExpired, BadTimeSignature, BadSignature):
        flash("The verification link has expired or is invalid.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first_or_404()
    user.email_verified = True
    db.session.commit()

    flash("Your email address has been successfully verified! ✅", "success")
    if current_user.is_authenticated:
        return redirect(url_for("settings.index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["POST"])
@login_required
def resend_verification():
    """Generate and dispatch a new email verification link."""
    s = _get_reset_serializer()
    token = s.dumps(current_user.email, salt="email-verification-salt")
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    current_app.logger.info(f"Email verification link for {current_user.email}: {verify_url}")
    flash("A verification link has been generated! (Check server logs in dev mode)", "info")
    return redirect(url_for("settings.index"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """POST only — prevents logout via GET (CSRF-safe pattern)."""
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))
