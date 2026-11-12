"""
tests/test_penny.py — Tests for Penny AI Finance Assistant routes.
"""

from decimal import Decimal
from datetime import date
from tests.conftest import login
from app import db
from app.models.user import User
from app.models.expense import Expense
from app.models.category import Category


class TestPennyChat:
    def test_penny_index_requires_login(self, client):
        """Unauthenticated user cannot access Penny chat UI."""
        resp = client.get("/penny", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_penny_chat_endpoint_without_key_returns_fallback(self, client, app):
        """When GEMINI_API_KEY is not configured, Penny returns a graceful fallback message."""
        with app.app_context():
            u = User(name="Penny Tester", email="pennytest@example.com", currency="INR")
            u.set_password("pass1234")
            db.session.add(u)
            db.session.commit()

        login(client, "pennytest@example.com", "pass1234")

        # GET chat page
        resp = client.get("/penny")
        assert resp.status_code == 200
        assert b"Penny" in resp.data

        # POST chat message
        resp = client.post(
            "/penny/chat",
            json={"message": "How much did I spend this month?"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data
        assert len(data["reply"]) > 10

    def test_penny_chat_empty_message_rejected(self, client, app):
        """Empty message should return 400 Bad Request."""
        with app.app_context():
            u = User.query.filter_by(email="pennytest@example.com").first()
            if not u:
                u = User(name="Penny Tester", email="pennytest@example.com", currency="INR")
                u.set_password("pass1234")
                db.session.add(u)
                db.session.commit()

        login(client, "pennytest@example.com", "pass1234")

        resp = client.post("/penny/chat", json={"message": "   "})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_penny_context_builder(self, app):
        """Verify build_financial_context runs without exceptions."""
        from app.penny.context import build_financial_context

        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()
            u = User.query.filter_by(email="pennytest@example.com").first()
            if not u:
                u = User(name="Penny Tester", email="pennytest@example.com", currency="INR")
                u.set_password("pass1234")
                db.session.add(u)
                db.session.flush()

            exp = Expense(
                user_id=u.id,
                category_id=cat.id,
                amount=Decimal("450.00"),
                currency="INR",
                description="Groceries context test",
                expense_date=date.today(),
                payment_method="UPI",
            )
            db.session.add(exp)
            db.session.commit()

            ctx = build_financial_context(u)
            assert "PENNYWISE FINANCIAL CONTEXT" in ctx
            assert "INR" in ctx
            assert "Groceries context test" in ctx or "Food" in ctx
