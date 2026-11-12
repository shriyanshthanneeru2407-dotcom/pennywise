"""
tests/test_recurring.py — Recurring subscriptions and expense tests for PennyWise.
"""

from datetime import date
from decimal import Decimal
from app import db
from app.models.user import User
from app.models.category import Category
from app.models.recurring import RecurringExpense
from app.models.expense import Expense
from tests.conftest import login


class TestRecurringExpenses:
    def _create_user(self, app, email="recurring@test.com"):
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name="Recurring User", email=email, currency="INR")
                u.set_password("pass1234")
                db.session.add(u)
                db.session.commit()
            return u.id

    def test_add_recurring_expense(self, client, app):
        """User can create an active recurring expense with next due date."""
        uid = self._create_user(app, "rec_add@test.com")
        login(client, "rec_add@test.com", "pass1234")

        with app.app_context():
            cat = Category.query.filter_by(name="Utilities").first() or Category.query.first()
            cat_id = cat.id

        today = date.today()
        resp = client.post("/recurring/new", data={
            "description": "Internet Fiber Broadband",
            "amount": "999.00",
            "category_id": str(cat_id),
            "frequency": "Monthly",
            "next_due_date": today.isoformat(),
            "payment_method": "UPI",
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert b"Recurring expense added" in resp.data

        with app.app_context():
            rec = RecurringExpense.query.filter_by(user_id=uid, description="Internet Fiber Broadband").first()
            assert rec is not None
            assert rec.amount == Decimal("999.00")
            assert rec.active is True

    def test_toggle_recurring_active_status(self, client, app):
        """User can toggle a recurring subscription between active and paused."""
        uid = self._create_user(app, "rec_toggle@test.com")
        login(client, "rec_toggle@test.com", "pass1234")

        with app.app_context():
            cat = Category.query.first()
            rec = RecurringExpense(
                user_id=uid,
                category_id=cat.id,
                description="Gym Subscription",
                amount=Decimal("1500.00"),
                currency="INR",
                frequency="Monthly",
                next_due_date=date.today(),
                active=True,
            )
            db.session.add(rec)
            db.session.commit()
            rec_id = rec.id

        # Pause
        resp = client.post(f"/recurring/{rec_id}/toggle", follow_redirects=True)
        assert resp.status_code == 200
        assert b"paused" in resp.data.lower()

        with app.app_context():
            rec = db.session.get(RecurringExpense, rec_id)
            assert rec.active is False

        # Reactivate
        resp2 = client.post(f"/recurring/{rec_id}/toggle", follow_redirects=True)
        assert resp2.status_code == 200
        assert b"activated" in resp2.data.lower()

        with app.app_context():
            rec = db.session.get(RecurringExpense, rec_id)
            assert rec.active is True

    def test_log_recurring_as_actual_expense(self, client, app):
        """Logging a recurring expense generates a transaction and advances next due date."""
        uid = self._create_user(app, "rec_log@test.com")
        login(client, "rec_log@test.com", "pass1234")

        initial_due = date.today()
        with app.app_context():
            cat = Category.query.first()
            rec = RecurringExpense(
                user_id=uid,
                category_id=cat.id,
                description="Cloud Storage Plan",
                amount=Decimal("199.00"),
                currency="INR",
                frequency="Monthly",
                next_due_date=initial_due,
                active=True,
            )
            db.session.add(rec)
            db.session.commit()
            rec_id = rec.id

        resp = client.post(f"/recurring/{rec_id}/log", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Expense logged" in resp.data

        with app.app_context():
            rec = db.session.get(RecurringExpense, rec_id)
            # Due date must have advanced by 1 month
            assert rec.next_due_date > initial_due
            # Transaction must be logged in Expense table
            exp = Expense.query.filter_by(user_id=uid, description="Cloud Storage Plan").first()
            assert exp is not None
            assert exp.amount == Decimal("199.00")
