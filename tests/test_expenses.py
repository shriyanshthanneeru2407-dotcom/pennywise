"""
tests/test_expenses.py — Expense CRUD and ownership tests.

KEY SECURITY TEST (Section 54 of spec):
  User A owns expense 100.
  User B attempts /expenses/100/edit → must be rejected (404).
"""

import pytest
from datetime import date
from decimal import Decimal
from tests.conftest import login, logout
from app.models.user import User
from app.models.expense import Expense
from app.models.category import Category
from app import db


def get_food_category(app):
    """Helper to get the Food category ID."""
    with app.app_context():
        cat = Category.query.filter_by(name="Food").first()
        return cat.id if cat else 1


class TestExpenseCRUD:
    def _login_new_user(self, client, app, email="expense_user@test.com"):
        with app.app_context():
            u = User(name="Expense User", email=email, currency="INR")
            u.set_password("password123")
            db.session.add(u)
            db.session.commit()
        login(client, email, "password123")
        return email

    def test_add_expense_success(self, client, app):
        """User can add a valid expense."""
        self._login_new_user(client, app, "add_test@test.com")
        cat_id = get_food_category(app)

        resp = client.post("/expenses/new", data={
            "amount": "500.00",
            "category_id": str(cat_id),
            "description": "Test lunch",
            "expense_date": date.today().isoformat(),
            "payment_method": "UPI",
            "notes": "",
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert b"added successfully" in resp.data.lower()

        with app.app_context():
            user = User.query.filter_by(email="add_test@test.com").first()
            expense = Expense.query.filter_by(user_id=user.id, description="Test lunch").first()
            assert expense is not None
            assert expense.amount == Decimal("500.00")
            assert expense.payment_method == "UPI"

    def test_add_expense_zero_amount(self, client, app):
        """Zero amount is rejected."""
        self._login_new_user(client, app, "zero_test@test.com")
        cat_id = get_food_category(app)

        resp = client.post("/expenses/new", data={
            "amount": "0",
            "category_id": str(cat_id),
            "description": "Invalid",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        }, follow_redirects=True)

        assert b"greater than zero" in resp.data.lower()

    def test_add_expense_negative_amount(self, client, app):
        """Negative amount is rejected."""
        self._login_new_user(client, app, "neg_test@test.com")
        cat_id = get_food_category(app)

        resp = client.post("/expenses/new", data={
            "amount": "-100",
            "category_id": str(cat_id),
            "description": "Invalid",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        }, follow_redirects=True)

        assert b"greater than zero" in resp.data.lower()

    def test_add_expense_missing_description(self, client, app):
        """Missing description is rejected."""
        self._login_new_user(client, app, "nodesc_test@test.com")
        cat_id = get_food_category(app)

        resp = client.post("/expenses/new", data={
            "amount": "100",
            "category_id": str(cat_id),
            "description": "",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        }, follow_redirects=True)

        assert b"required" in resp.data.lower()

    def test_edit_own_expense(self, client, app):
        """User can edit their own expense."""
        self._login_new_user(client, app, "edit_owner@test.com")
        cat_id = get_food_category(app)

        # Add an expense
        client.post("/expenses/new", data={
            "amount": "300.00",
            "category_id": str(cat_id),
            "description": "Original description",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        })

        with app.app_context():
            user = User.query.filter_by(email="edit_owner@test.com").first()
            expense = Expense.query.filter_by(user_id=user.id).first()
            expense_id = expense.id

        # Edit it
        resp = client.post(f"/expenses/{expense_id}/edit", data={
            "amount": "350.00",
            "category_id": str(cat_id),
            "description": "Updated description",
            "expense_date": date.today().isoformat(),
            "payment_method": "UPI",
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert b"updated successfully" in resp.data.lower()

        with app.app_context():
            updated = db.session.get(Expense, expense_id)
            assert updated.amount == Decimal("350.00")
            assert updated.description == "Updated description"

    def test_delete_own_expense(self, client, app):
        """User can delete their own expense."""
        self._login_new_user(client, app, "delete_owner@test.com")
        cat_id = get_food_category(app)

        client.post("/expenses/new", data={
            "amount": "200.00",
            "category_id": str(cat_id),
            "description": "To be deleted",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        })

        with app.app_context():
            user = User.query.filter_by(email="delete_owner@test.com").first()
            expense = Expense.query.filter_by(user_id=user.id, description="To be deleted").first()
            expense_id = expense.id

        resp = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
        assert resp.status_code == 200
        assert b"deleted" in resp.data.lower()

        with app.app_context():
            assert db.session.get(Expense, expense_id) is None


class TestOwnershipSecurity:
    """
    CRITICAL SECURITY TESTS.

    These tests verify that User B cannot access, edit, or delete
    expenses belonging to User A — even if they know the expense ID.
    """

    def _create_expense_for_user(self, app, user_id, cat_id):
        """Helper to create an expense owned by a specific user."""
        with app.app_context():
            expense = Expense(
                user_id=user_id,
                category_id=cat_id,
                amount=Decimal("1000.00"),
                currency="INR",
                description="User A's private expense",
                expense_date=date.today(),
                payment_method="Cash",
            )
            db.session.add(expense)
            db.session.commit()
            return expense.id

    def test_user_b_cannot_edit_user_a_expense(self, client, app):
        """
        THE KEY SECURITY TEST (Section 54 of spec).
        User B must not be able to edit User A's expense.
        """
        cat_id = get_food_category(app)

        # Create User A's expense
        with app.app_context():
            user_a = User(name="Security A", email="sec_a@test.com", currency="INR")
            user_a.set_password("passwordA")
            db.session.add(user_a)
            db.session.commit()
            expense_id = self._create_expense_for_user(app, user_a.id, cat_id)

        # Log in as User B
        with app.app_context():
            user_b = User(name="Security B", email="sec_b@test.com", currency="INR")
            user_b.set_password("passwordB")
            db.session.add(user_b)
            db.session.commit()

        login(client, "sec_b@test.com", "passwordB")

        # Attempt to access User A's expense edit form
        resp = client.get(f"/expenses/{expense_id}/edit")
        assert resp.status_code == 404, (
            f"Expected 404, got {resp.status_code}. "
            "User B should not be able to access User A's expense."
        )

    def test_user_b_cannot_delete_user_a_expense(self, client, app):
        """User B must not be able to delete User A's expense."""
        cat_id = get_food_category(app)

        with app.app_context():
            user_a = User(name="Del A", email="del_a@test.com", currency="INR")
            user_a.set_password("passwordA")
            db.session.add(user_a)
            db.session.commit()
            expense_id = self._create_expense_for_user(app, user_a.id, cat_id)

        with app.app_context():
            user_b = User(name="Del B", email="del_b@test.com", currency="INR")
            user_b.set_password("passwordB")
            db.session.add(user_b)
            db.session.commit()

        login(client, "del_b@test.com", "passwordB")

        # Attempt to delete User A's expense
        resp = client.post(f"/expenses/{expense_id}/delete")
        assert resp.status_code == 404, (
            "User B should not be able to delete User A's expense."
        )

        # Expense should still exist
        with app.app_context():
            expense = db.session.get(Expense, expense_id)
            assert expense is not None, "Expense was deleted by unauthorized user!"

    def test_unauthenticated_cannot_access_expense(self, client, app):
        """Unauthenticated request to an expense should redirect to login."""
        resp = client.get("/expenses/999/edit", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.location
