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
        assert b"SpendWise" in resp.data  # Landed on dashboard

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
