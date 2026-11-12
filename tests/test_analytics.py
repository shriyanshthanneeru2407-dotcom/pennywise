"""
tests/test_analytics.py — Analytics engine tests.

Verifies all calculations are correct, including edge cases:
  - Zero previous-month spending (division by zero safety)
  - No expenses
  - Single transaction
  - Large numbers
"""

from datetime import date
from decimal import Decimal
from app.models.user import User
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.category import Category
from app.services import analytics
from app import db


class TestAnalytics:
    def _make_user(self, db, app, email="analytics@test.com"):
        with app.app_context():
            u = User(name="Analytics User", email=email, currency="INR")
            u.set_password("password")
            db.session.add(u)
            db.session.commit()
            return u.id

    def _add_expense(self, app, user_id, amount, month=None):
        today = date.today()
        expense_date = date(today.year, month or today.month, 15)
        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()
            e = Expense(
                user_id=user_id,
                category_id=cat.id,
                amount=Decimal(str(amount)),
                currency="INR",
                description=f"Test expense {amount}",
                expense_date=expense_date,
                payment_method="Cash",
            )
            db.session.add(e)
            db.session.commit()

    def test_monthly_summary_no_expenses(self, db, app):
        """Summary with no expenses returns zero total and count."""
        user_id = self._make_user(db, app, "no_expenses@test.com")
        today = date.today()

        with app.app_context():
            summary = analytics.get_monthly_summary(user_id, today.year, today.month)

        assert summary["total"] == Decimal("0")
        assert summary["count"] == 0
        assert summary["budget"] is None
        assert summary["remaining"] is None

    def test_monthly_summary_with_expenses(self, db, app):
        """Summary correctly totals multiple expenses."""
        user_id = self._make_user(db, app, "with_expenses@test.com")
        today = date.today()

        self._add_expense(app, user_id, "500.00")
        self._add_expense(app, user_id, "300.00")
        self._add_expense(app, user_id, "200.00")

        with app.app_context():
            summary = analytics.get_monthly_summary(user_id, today.year, today.month)

        assert summary["total"] == Decimal("1000.00")
        assert summary["count"] == 3

    def test_monthly_summary_income_and_net_balance(self, db, app):
        """Summary computes cash flow: total income, expenses, net balance, and savings rate."""
        user_id = self._make_user(db, app, "cashflow@test.com")
        today = date.today()

        with app.app_context():
            food = Category.query.filter_by(name="Food").first()
            salary_cat = Category.query.filter_by(name="Salary").first() or food

            # Add Income: 50,000
            inc = Expense(
                user_id=user_id,
                category_id=salary_cat.id,
                amount=Decimal("50000.00"),
                currency="INR",
                description="Monthly Salary",
                expense_date=date(today.year, today.month, 1),
                payment_method="Bank Transfer",
                transaction_type="income",
            )
            # Add Expense: 15,000
            exp = Expense(
                user_id=user_id,
                category_id=food.id,
                amount=Decimal("15000.00"),
                currency="INR",
                description="Groceries",
                expense_date=date(today.year, today.month, 5),
                payment_method="UPI",
                transaction_type="expense",
            )
            db.session.add_all([inc, exp])
            db.session.commit()

            summary = analytics.get_monthly_summary(user_id, today.year, today.month)

        assert summary["total_income"] == Decimal("50000.00")
        assert summary["total_expenses"] == Decimal("15000.00")
        assert summary["net_balance"] == Decimal("35000.00")
        assert summary["savings_rate"] == 70.0

    def test_monthly_comparison_zero_previous(self, db, app):
        """
        Monthly comparison when previous month has zero spending.
        Must not divide by zero — should return change_pct = None.
        """
        user_id = self._make_user(db, app, "zero_prev@test.com")

        # Only add current month expenses (no previous month)
        self._add_expense(app, user_id, "1000.00")

        with app.app_context():
            comparison = analytics.get_monthly_comparison(user_id)

        # With zero previous month, we can't compute a meaningful percentage
        assert comparison["change_pct"] is None

    def test_category_totals(self, db, app):
        """Category totals are correctly calculated and sorted by amount."""
        user_id = self._make_user(db, app, "cat_totals@test.com")
        today = date.today()

        self._add_expense(app, user_id, "500.00")
        self._add_expense(app, user_id, "500.00")

        with app.app_context():
            cats = analytics.get_category_totals(user_id, today.year, today.month)

        assert len(cats) > 0
        # Should be sorted by total descending
        for i in range(len(cats) - 1):
            assert cats[i]["total"] >= cats[i + 1]["total"]

    def test_insights_no_expenses(self, db, app):
        """Insights returns appropriate message when no expenses."""
        user_id = self._make_user(db, app, "no_exp_insights@test.com")

        with app.app_context():
            insights = analytics.get_insights(user_id)

        assert len(insights) > 0
        assert insights[0]["type"] == "info"

    def test_budget_percentage_over_budget(self, db, app):
        """Budget percentage > 100 when over budget."""
        user_id = self._make_user(db, app, "over_budget@test.com")
        today = date.today()

        with app.app_context():
            budget = Budget(
                user_id=user_id,
                year=today.year,
                month=today.month,
                amount=Decimal("1000.00"),
                currency="INR",
            )
            db.session.add(budget)
            db.session.commit()

        # Add more than the budget
        self._add_expense(app, user_id, "1500.00")

        with app.app_context():
            summary = analytics.get_monthly_summary(user_id, today.year, today.month)

        assert summary["budget_pct"] > 100
        assert summary["remaining"] < 0

    def test_safe_divide_zero_denominator(self, db, app):
        """_safe_divide never raises ZeroDivisionError."""
        from app.services.analytics import _safe_divide
        result = _safe_divide(Decimal("100"), Decimal("0"))
        assert result == Decimal("0")

        result = _safe_divide(Decimal("100"), 0)
        assert result == Decimal("0")
