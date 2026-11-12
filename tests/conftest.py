"""
tests/conftest.py — pytest fixtures shared across all test files.

Creates a fresh in-memory SQLite database for each test function.
No data persists between tests.
"""

import pytest
from app import create_app, db as _db
from app.models.category import Category, DEFAULT_CATEGORIES


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask app configured for testing.
    Uses an in-memory SQLite database so tests are fast, isolated,
    and NEVER touch or drop the development database in instance/spendwise.db.
    """
    test_app = create_app("testing")

    with test_app.app_context():
        _db.create_all()
        _seed_categories()
        yield test_app
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean all tables between tests so every test has complete isolation."""
    with app.app_context():
        yield
        _db.session.rollback()
        # Delete data from all user tables (keep categories)
        for table in reversed(_db.metadata.sorted_tables):
            if table.name != "categories":
                _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean database state for each test."""
    with app.app_context():
        yield _db
        _db.session.remove()


@pytest.fixture(scope="function")
def client(app):
    """Flask test client with clean cookie jar."""
    c = app.test_client()
    return c


def _seed_categories():
    """Seed default categories so tests can reference them."""
    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(user_id=None, name=cat_data["name"]).first()
        if not existing:
            cat = Category(user_id=None, **cat_data)
            _db.session.add(cat)
    _db.session.commit()


def login(client, email, password):
    """Helper to log in a user via the test client (clears existing session first)."""
    # Clear any previous session so the login endpoint processes the request
    client.post("/auth/logout", follow_redirects=True)
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def logout(client):
    """Helper to log out."""
    return client.post("/auth/logout", follow_redirects=True)
