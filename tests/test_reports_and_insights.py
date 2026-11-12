"""
tests/test_reports_and_insights.py — Tests for Insights, Reports, CSV Export & Error Pages
"""

from datetime import date
from decimal import Decimal
from app import db
from app.models.user import User
from app.models.category import Category
from app.models.expense import Expense
from tests.conftest import login


class TestInsightsAndReports:
    """Test suite covering Insights, 12-Month Reports, and CSV Export."""

    def _login_test_user(self, client, app, email="reports_user@test.com"):
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name="Reports Tester", email=email, currency="INR")
                u.set_password("password123")
                db.session.add(u)
                db.session.commit()
            uid = u.id
        login(client, email, "password123")
        return uid

    def test_insights_page_loads_with_data(self, client, app):
        """Verify the /insights route loads with real user financial data."""
        uid = self._login_test_user(client, app)
        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()
            exp = Expense(
                user_id=uid,
                category_id=cat.id,
                amount=Decimal("150.00"),
                expense_date=date.today(),
                description="Insights Dinner",
                transaction_type="expense",
            )
            db.session.add(exp)
            db.session.commit()

        resp = client.get("/insights")
        assert resp.status_code == 200
        assert b"Insights" in resp.data or b"Observations" in resp.data

    def test_insights_requires_login(self, client):
        """Verify unauthenticated requests redirect to login."""
        resp = client.get("/insights")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_reports_page_loads(self, client, app):
        """Verify the /reports route loads the annual performance matrix."""
        self._login_test_user(client, app)
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert b"Reports" in resp.data or b"Performance" in resp.data

    def test_csv_export_endpoint(self, client, app):
        """Verify /reports/export.csv produces a valid RFC 4180 CSV response."""
        uid = self._login_test_user(client, app)
        with app.app_context():
            cat = Category.query.filter_by(name="Salary").first()
            inc = Expense(
                user_id=uid,
                category_id=cat.id,
                amount=Decimal("5000.00"),
                expense_date=date.today(),
                description="Monthly Paycheck",
                transaction_type="income",
            )
            db.session.add(inc)
            db.session.commit()

        resp = client.get("/reports/export.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("Content-Type", "")
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        content = resp.data.decode("utf-8")
        assert "Date" in content and "Category" in content and "Amount" in content
        assert "Monthly Paycheck" in content
        assert "5000.00" in content

    def test_custom_404_page(self, client):
        """Verify non-existent routes trigger the custom branded 404 handler."""
        resp = client.get("/this-route-does-not-exist-at-all-404")
        assert resp.status_code == 404
        assert b"Page not found" in resp.data
        assert b"PennyWise" in resp.data
