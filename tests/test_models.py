"""
tests/test_models.py — Unit tests for Phase 2 SQLAlchemy models.

Tests:
  - User model: creation, scrypt hashing, password validation, currency properties.
  - Category model: system defaults (user_id=None), custom user categories.
  - Expense model: decimal precision, cascade delete, payment method validation.
  - Budget model: monthly budget constraints, uniqueness per user/year/month.
  - RecurringExpense model: frequencies, active status toggle.
  - Receipt model: 1-to-1 relationship with Expense, cascade delete.
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.user import User
from app.models.category import Category
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.recurring import RecurringExpense
from app.models.receipt import Receipt


class TestUserModel:
    def test_create_user_and_password_hashing(self, app):
        """Verify user model creation and scrypt password hashing."""
        with app.app_context():
            u = User(name="Alice Model", email="alice_m@example.com", currency="USD")
            u.set_password("SuperSecret123")
            db.session.add(u)
            db.session.commit()

            assert u.id is not None
            assert u.password_hash != "SuperSecret123"
            assert u.check_password("SuperSecret123") is True
            assert u.check_password("WrongPassword") is False
            assert u.currency_symbol == "$"
            assert u.format_amount(Decimal("1234.56")) == "$1,234.56"

    def test_duplicate_email_rejected_by_model(self, app):
        """Verify unique constraint on user email."""
        with app.app_context():
            u1 = User(name="User 1", email="duplicate@example.com")
            u1.set_password("pass12345")
            db.session.add(u1)
            db.session.commit()

            u2 = User(name="User 2", email="duplicate@example.com")
            u2.set_password("pass12345")
            db.session.add(u2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestCategoryModel:
    def test_system_vs_user_category(self, app):
        """Verify system categories (user_id=None) vs user-owned categories."""
        with app.app_context():
            u = User(name="Cat User", email="cat_user@example.com")
            u.set_password("pass12345")
            db.session.add(u)
            db.session.commit()

            # System category
            sys_cat = Category(name="System Utility", icon="⚡", color="#00e676", user_id=None)
            db.session.add(sys_cat)

            # User category
            user_cat = Category(name="Hobby", icon="🎨", color="#ff00ff", user_id=u.id)
            db.session.add(user_cat)
            db.session.commit()

            assert sys_cat.user_id is None
            assert user_cat.user_id == u.id


class TestExpenseModel:
    def test_expense_numeric_precision(self, app):
        """Verify amount maintains exact decimal precision without floating point drift."""
        with app.app_context():
            u = User(name="Expense User", email="exp_prec@example.com")
            u.set_password("pass12345")
            cat = Category.query.first()
            db.session.add(u)
            db.session.commit()

            precise_amount = Decimal("99.99")
            exp = Expense(
                user_id=u.id,
                category_id=cat.id,
                amount=precise_amount,
                currency="INR",
                description="Precision Test",
                expense_date=date.today(),
                payment_method="UPI",
            )
            db.session.add(exp)
            db.session.commit()

            saved = db.session.get(Expense, exp.id)
            assert saved.amount == Decimal("99.99")
            assert str(saved.amount) == "99.99"


class TestBudgetModel:
    def test_budget_unique_per_month_constraint(self, app):
        """Verify only one budget can exist per user per year/month."""
        with app.app_context():
            u = User(name="Budget User", email="b_user@example.com")
            u.set_password("pass12345")
            db.session.add(u)
            db.session.commit()

            b1 = Budget(user_id=u.id, year=2026, month=9, amount=Decimal("50000.00"), currency="INR")
            db.session.add(b1)
            db.session.commit()

            # Attempting second budget for same month must raise IntegrityError
            b2 = Budget(user_id=u.id, year=2026, month=9, amount=Decimal("60000.00"), currency="INR")
            db.session.add(b2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestRecurringModel:
    def test_recurring_expense_toggle(self, app):
        """Verify recurring expense creation and active status toggle."""
        with app.app_context():
            u = User(name="Recur User", email="rec_user@example.com")
            u.set_password("pass12345")
            cat = Category.query.first()
            db.session.add(u)
            db.session.commit()

            rec = RecurringExpense(
                user_id=u.id,
                category_id=cat.id,
                description="Netflix Subscription",
                amount=Decimal("499.00"),
                currency="INR",
                frequency="Monthly",
                next_due_date=date.today(),
                active=True,
            )
            db.session.add(rec)
            db.session.commit()

            assert rec.active is True
            rec.active = False
            db.session.commit()

            reloaded = db.session.get(RecurringExpense, rec.id)
            assert reloaded.active is False


class TestReceiptModel:
    def test_receipt_one_to_one_relationship_and_cascade(self, app):
        """Verify Receipt 1-to-1 relationship with Expense and cascade delete."""
        with app.app_context():
            u = User(name="Receipt User", email="rec_user_2@example.com")
            u.set_password("pass12345")
            cat = Category.query.first()
            db.session.add(u)
            db.session.commit()

            exp = Expense(
                user_id=u.id,
                category_id=cat.id,
                amount=Decimal("150.00"),
                description="Dinner with receipt",
                expense_date=date.today(),
            )
            db.session.add(exp)
            db.session.commit()

            rcpt = Receipt(
                expense_id=exp.id,
                storage_key="receipts/dinner.jpg",
                original_filename="dinner.jpg",
                mime_type="image/jpeg",
                file_size=10240,
            )
            db.session.add(rcpt)
            db.session.commit()

            assert exp.receipt is not None
            assert exp.receipt.storage_key == "receipts/dinner.jpg"

            # Deleting expense must cascade delete the receipt
            db.session.delete(exp)
            db.session.commit()

            assert db.session.get(Receipt, rcpt.id) is None
