"""
tests/test_budgets.py — Comprehensive tests for Monthly and Category Budgets.

Covers:
  - Setting overall monthly budget
  - Setting category spending caps
  - Deleting category spending caps
  - Validation of negative or zero values
  - Isolation between users
"""

from datetime import date
from decimal import Decimal
from app import db
from app.models.user import User
from app.models.budget import Budget, CategoryBudget
from app.models.category import Category
from tests.conftest import login


class TestBudgetManagement:
    def _create_and_login_user(self, client, app, email="budget_user@test.com"):
        with app.app_context():
            user = User(name="Budget User", email=email, currency="INR")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        login(client, email, "password123")
        return user_id

    def test_set_and_update_monthly_budget(self, client, app):
        """User can set an overall monthly budget and update it."""
        user_id = self._create_and_login_user(client, app, "budget_set@test.com")

        # 1. Set budget
        resp = client.post("/budget/set", data={"amount": "45000"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Monthly budget updated successfully" in resp.data

        today = date.today()
        with app.app_context():
            b = Budget.query.filter_by(
                user_id=user_id, year=today.year, month=today.month
            ).first()
            assert b is not None
            assert b.amount == Decimal("45000")

        # 2. Update budget
        resp2 = client.post("/budget/set", data={"amount": "60000"}, follow_redirects=True)
        assert resp2.status_code == 200
        with app.app_context():
            b = Budget.query.filter_by(
                user_id=user_id, year=today.year, month=today.month
            ).first()
            assert b.amount == Decimal("60000")

    def test_set_invalid_monthly_budget_amount(self, client, app):
        """Zero and negative budget amounts are rejected."""
        self._create_and_login_user(client, app, "budget_invalid@test.com")

        resp = client.post("/budget/set", data={"amount": "0"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Budget amount must be greater than zero" in resp.data

        resp2 = client.post("/budget/set", data={"amount": "-500"}, follow_redirects=True)
        assert resp2.status_code == 200
        assert b"Budget amount must be greater than zero" in resp2.data

    def test_set_and_delete_category_budget(self, client, app):
        """User can set a category budget and remove it."""
        user_id = self._create_and_login_user(client, app, "budget_cat@test.com")

        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()
            assert cat is not None
            cat_id = cat.id

        today = date.today()
        # Set category budget
        resp = client.post(
            "/budget/category/set",
            data={"category_id": str(cat_id), "amount": "12000"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Budget for Food set to" in resp.data

        with app.app_context():
            cb = CategoryBudget.query.filter_by(
                user_id=user_id, category_id=cat_id, year=today.year, month=today.month
            ).first()
            assert cb is not None
            assert cb.amount == Decimal("12000")
            cb_id = cb.id

        # Delete category budget
        resp2 = client.post(f"/budget/category/{cb_id}/delete", follow_redirects=True)
        assert resp2.status_code == 200
        assert b"Budget limit for Food removed" in resp2.data

        with app.app_context():
            cb_deleted = db.session.get(CategoryBudget, cb_id)
            assert cb_deleted is None

    def test_category_budget_cross_user_isolation(self, client, app):
        """User B cannot delete User A's category budget."""
        with app.app_context():
            user_a = User(name="User A", email="usera_cb@test.com", currency="INR")
            user_a.set_password("pass123")
            user_b = User(name="User B", email="userb_cb@test.com", currency="INR")
            user_b.set_password("pass123")
            db.session.add_all([user_a, user_b])
            db.session.commit()

            cat = Category.query.filter_by(name="Shopping").first()
            today = date.today()
            cb = CategoryBudget(
                user_id=user_a.id,
                category_id=cat.id,
                year=today.year,
                month=today.month,
                amount=Decimal("5000"),
            )
            db.session.add(cb)
            db.session.commit()
            cb_id = cb.id

        # User B logs in and tries to delete it
        login(client, "userb_cb@test.com", "pass123")
        resp = client.post(f"/budget/category/{cb_id}/delete")
        assert resp.status_code == 404

        # Budget should still exist
        with app.app_context():
            assert db.session.get(CategoryBudget, cb_id) is not None
