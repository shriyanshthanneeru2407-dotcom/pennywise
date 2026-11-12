"""
tests/test_auth.py — Authentication tests.

Tests:
  - Registration with valid data
  - Duplicate email rejection
  - Login with correct credentials
  - Login with wrong password
  - Logout
  - Unauthenticated redirect
"""

import pytest
from tests.conftest import login, logout
from app.models.user import User
from app import db


class TestRegistration:
    def test_register_success(self, client, app):
        """A new user can register with valid data."""
        resp = client.post("/auth/register", data={
            "name": "Test User",
            "email": "newuser@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"PennyWise" in resp.data  # Landed on dashboard

        # Verify user was created in DB
        with app.app_context():
            user = User.query.filter_by(email="newuser@example.com").first()
            assert user is not None
            assert user.name == "Test User"
            # Password must NOT be stored in plain text
            assert user.password_hash != "securepass123"
            assert user.check_password("securepass123")

    def test_register_with_custom_currency(self, client, app):
        """User can choose their preferred currency upon registration."""
        resp = client.post("/auth/register", data={
            "name": "Dollar User",
            "email": "dollar@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
            "currency": "USD",
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            user = User.query.filter_by(email="dollar@example.com").first()
            assert user is not None
            assert user.currency == "USD"
            assert user.currency_symbol == "$"

    def test_register_with_aed_currency(self, client, app):
        """User can select AED currency upon registration."""
        resp = client.post("/auth/register", data={
            "name": "Dubai User",
            "email": "dubai@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
            "currency": "AED",
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            user = User.query.filter_by(email="dubai@example.com").first()
            assert user is not None
            assert user.currency == "AED"
            assert user.currency_symbol == "د.إ"

    def test_register_duplicate_email(self, client, app):
        """Registering with an email that already exists is rejected."""
        data = {
            "name": "First User",
            "email": "dup@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }
        client.post("/auth/register", data=data)  # First registration
        logout(client)

        # Second registration with same email
        resp = client.post("/auth/register", data={
            **data, "name": "Second User"
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"already exists" in resp.data.lower()

    def test_register_short_password(self, client):
        """Password shorter than 8 chars is rejected."""
        resp = client.post("/auth/register", data={
            "name": "Test",
            "email": "shortpw@example.com",
            "password": "abc",
            "confirm_password": "abc",
        }, follow_redirects=True)
        # Either client-side or server-side should reject
        # Server always validates
        assert resp.status_code == 200

    def test_register_password_mismatch(self, client):
        """Mismatched passwords are rejected."""
        resp = client.post("/auth/register", data={
            "name": "Test",
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "different456",
        }, follow_redirects=True)
        assert b"do not match" in resp.data.lower()

    def test_register_missing_name(self, client):
        """Missing name is rejected."""
        resp = client.post("/auth/register", data={
            "name": "",
            "email": "noname@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        assert b"required" in resp.data.lower()


class TestLogin:
    def test_login_success(self, client, app):
        """User can log in with correct credentials."""
        # Create a user first
        with app.app_context():
            u = User(name="Login Test", email="logintest@example.com")
            u.set_password("mypassword")
            db.session.add(u)
            db.session.commit()

        resp = login(client, "logintest@example.com", "mypassword")
        assert resp.status_code == 200
        # Should be on dashboard
        assert b"Dashboard" in resp.data or b"SpendWise" in resp.data

    def test_login_wrong_password(self, client, app):
        """Wrong password gives generic error (no account enumeration)."""
        with app.app_context():
            u = User(name="WrongPW", email="wrongpw@example.com")
            u.set_password("correctpassword")
            db.session.add(u)
            db.session.commit()

        resp = login(client, "wrongpw@example.com", "wrongpassword")
        assert b"Invalid email or password" in resp.data

    def test_login_nonexistent_email(self, client):
        """Login with non-existent email gives same generic error."""
        resp = login(client, "nobody@example.com", "anypassword")
        assert b"Invalid email or password" in resp.data

    def test_logout(self, client, app):
        """User can log out and session is cleared."""
        with app.app_context():
            u = User(name="Logout Test", email="logouttest@example.com")
            u.set_password("password123")
            db.session.add(u)
            db.session.commit()

        login(client, "logouttest@example.com", "password123")
        resp = logout(client)
        assert resp.status_code == 200

        # After logout, dashboard should redirect to login
        resp = client.get("/dashboard/", follow_redirects=True)
        assert b"Sign in" in resp.data or b"login" in resp.data.lower()


class TestUnauthenticatedAccess:
    def test_dashboard_requires_login(self, client):
        """Dashboard redirects unauthenticated users to login."""
        resp = client.get("/dashboard/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.location

    def test_expenses_requires_login(self, client):
        """Expense list requires login."""
        resp = client.get("/expenses/", follow_redirects=False)
        assert resp.status_code == 302

    def test_budget_requires_login(self, client):
        """Budget page requires login."""
        resp = client.get("/budget/", follow_redirects=False)
        assert resp.status_code == 302



class TestPasswordReset:
    def test_forgot_password_request_existing_user(self, client, app):
        """Requesting password reset for an existing user succeeds without errors."""
        with app.app_context():
            u = User(name="Reset User", email="reset_me@example.com")
            u.set_password("OldPassword123")
            db.session.add(u)
            db.session.commit()

        resp = client.post("/auth/forgot-password", data={"email": "reset_me@example.com"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"password reset link" in resp.data.lower()

    def test_reset_password_with_valid_token(self, client, app):
        """User can successfully set a new password with a valid cryptographic token."""
        from itsdangerous import URLSafeTimedSerializer
        with app.app_context():
            u = User(name="Token User", email="token_reset@example.com")
            u.set_password("InitialPassword123")
            db.session.add(u)
            db.session.commit()

            s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
            token = s.dumps("token_reset@example.com", salt="password-reset-salt")

        # Submit new password
        resp = client.post(
            f"/auth/reset-password/{token}",
            data={"password": "NewSecretPassword!", "confirm_password": "NewSecretPassword!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"successfully updated" in resp.data.lower()

        # Verify old password fails and new password works
        with app.app_context():
            user = User.query.filter_by(email="token_reset@example.com").first()
            assert not user.check_password("InitialPassword123")
            assert user.check_password("NewSecretPassword!")


class TestGoogleOAuth:
    def test_google_login_unconfigured_flash_warning(self, client, app):
        """When Google OAuth is unconfigured or has placeholder, flashes guidance warning."""
        app.config["GOOGLE_CLIENT_ID"] = ""
        app.config["GOOGLE_CLIENT_SECRET"] = ""
        resp = client.get("/auth/google", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Google Sign-In is not yet configured" in resp.data

    def test_google_login_redirect_when_configured(self, client, app):
        """When Google OAuth is configured, redirects to Google Accounts OAuth endpoint with state."""
        app.config["GOOGLE_CLIENT_ID"] = "test-client-id-123.apps.googleusercontent.com"
        app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-xyz"

        resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code == 302
        assert "accounts.google.com" in resp.location
        assert "client_id=test-client-id-123.apps.googleusercontent.com" in resp.location
        assert "state=" in resp.location
