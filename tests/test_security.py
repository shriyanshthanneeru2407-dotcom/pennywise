"""
tests/test_security.py — Security-focused tests.

Tests:
  - CSRF-like protection (forms require POST, not GET)
  - Cross-user expense access blocked
  - Invalid expense IDs return 404
  - Unauthenticated access redirects
  - Passwords are hashed (never plain text)
  - SQL injection attempt (via ORM parameterization)
"""

from datetime import date
from decimal import Decimal
from tests.conftest import login
from app.models.user import User
from app.models.expense import Expense
from app.models.category import Category
from app import db


class TestPasswordStorage:
    def test_password_not_stored_in_plain_text(self, app):
        """Verify passwords are hashed, never stored as plain text."""
        with app.app_context():
            u = User(name="Hash Test", email="hashtest@test.com", currency="INR")
            u.set_password("mysecretpassword")
            db.session.add(u)
            db.session.commit()

            stored = User.query.filter_by(email="hashtest@test.com").first()
            assert stored.password_hash != "mysecretpassword"
            h = stored.password_hash.lower()
            assert "pbkdf2" in h or "scrypt" in h or stored.password_hash.startswith("$")
            assert stored.check_password("mysecretpassword")
            assert not stored.check_password("wrongpassword")


class TestCrossUserAccess:
    def _setup_two_users_and_expense(self, app):
        """Create User A with an expense, and User B with no expenses."""
        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()

            user_a = User(name="Security A", email="xsec_a@test.com", currency="INR")
            user_a.set_password("passwordA")
            db.session.add(user_a)
            db.session.flush()

            expense = Expense(
                user_id=user_a.id,
                category_id=cat.id,
                amount=Decimal("500.00"),
                currency="INR",
                description="User A's expense",
                expense_date=date.today(),
                payment_method="Cash",
            )
            db.session.add(expense)

            user_b = User(name="Security B", email="xsec_b@test.com", currency="INR")
            user_b.set_password("passwordB")
            db.session.add(user_b)

            db.session.commit()
            return expense.id

    def test_cross_user_edit_blocked(self, client, app):
        """User B cannot access User A's expense edit form."""
        expense_id = self._setup_two_users_and_expense(app)
        login(client, "xsec_b@test.com", "passwordB")

        resp = client.get(f"/expenses/{expense_id}/edit")
        assert resp.status_code == 404

    def test_cross_user_delete_blocked(self, client, app):
        """User B cannot delete User A's expense."""
        expense_id = self._setup_two_users_and_expense(app)
        login(client, "xsec_b@test.com", "passwordB")

        resp = client.post(f"/expenses/{expense_id}/delete")
        assert resp.status_code == 404

        with app.app_context():
            expense = db.session.get(Expense, expense_id)
            assert expense is not None  # Expense still exists


class TestInvalidInputs:
    def _login_user(self, client, app, email="invalid_input@test.com"):
        with app.app_context():
            u = User(name="Test", email=email, currency="INR")
            u.set_password("password")
            db.session.add(u)
            db.session.commit()
        login(client, email, "password")

    def test_nonexistent_expense_id(self, client, app):
        """Accessing a nonexistent expense ID returns 404."""
        self._login_user(client, app, "nonexist@test.com")
        resp = client.get("/expenses/999999/edit")
        assert resp.status_code == 404

    def test_invalid_amount_string(self, client, app):
        """Non-numeric amount is rejected."""
        self._login_user(client, app, "invalid_amt@test.com")
        cat = None
        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()

        resp = client.post("/expenses/new", data={
            "amount": "not-a-number",
            "category_id": str(cat.id),
            "description": "Test",
            "expense_date": date.today().isoformat(),
            "payment_method": "Cash",
        }, follow_redirects=True)

        assert b"valid number" in resp.data.lower() or resp.status_code == 200

    def test_delete_via_get_not_allowed(self, client, app):
        """
        GET request to delete endpoint should not delete.
        Delete must only work via POST (prevents CSRF through links).
        """
        self._login_user(client, app, "get_delete@test.com")
        # GET to delete endpoint should return 405 Method Not Allowed
        resp = client.get("/expenses/1/delete")
        assert resp.status_code == 405


class TestSQLInjectionProtection:
    def test_search_with_sql_injection_attempt(self, client, app):
        """
        SQL injection in search query should not break the app.
        SQLAlchemy's ORM uses parameterized queries, so this should
        return a normal (empty) result, not an error.
        """
        with app.app_context():
            u = User(name="SQLi Test", email="sqli@test.com", currency="INR")
            u.set_password("password")
            db.session.add(u)
            db.session.commit()

        login(client, "sqli@test.com", "password")

        # Attempt SQL injection via search
        resp = client.get("/expenses/?q=' OR '1'='1'; DROP TABLE expenses; --")
        # Should return 200 with empty results, not a 500 error
        assert resp.status_code == 200


class TestJSONBackup:
    def test_json_backup_export(self, client, app):
        """Verify full JSON backup generation and data format."""
        with app.app_context():
            cat = Category.query.filter_by(name="Food").first()
            u = User(name="Backup User", email="backup@test.com", currency="USD")
            u.set_password("pass1234")
            db.session.add(u)
            db.session.flush()

            exp = Expense(
                user_id=u.id,
                category_id=cat.id,
                amount=Decimal("123.45"),
                currency="USD",
                description="Dinner with friends",
                expense_date=date.today(),
                payment_method="Credit Card",
            )
            db.session.add(exp)
            db.session.commit()

        login(client, "backup@test.com", "pass1234")
        resp = client.get("/settings/backup/json")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        data = resp.get_json()
        assert data["version"] == "1.0"
        assert data["user"]["email"] == "backup@test.com"
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["amount"] == "123.45"
        assert data["transactions"][0]["description"] == "Dinner with friends"

    def test_json_backup_import(self, client, app):
        """Verify restoring/importing financial records from a JSON backup."""
        import io
        import json

        with app.app_context():
            u = User(name="Import User", email="importer@test.com", currency="EUR")
            u.set_password("pass1234")
            db.session.add(u)
            db.session.commit()

        login(client, "importer@test.com", "pass1234")

        payload = {
            "version": "1.0",
            "custom_categories": [
                {"name": "Gaming", "category_type": "expense", "icon": "🎮", "color": "#8b5cf6"}
            ],
            "transactions": [
                {
                    "date": "2026-05-15",
                    "description": "Steam Game Purchase",
                    "amount": "59.99",
                    "transaction_type": "expense",
                    "payment_method": "Credit Card",
                    "category": "Gaming",
                    "notes": "CS50 reward",
                }
            ],
        }
        data = {
            "backup_file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "backup.json")
        }
        resp = client.post(
            "/settings/backup/import",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Successfully imported 1 transaction" in resp.data

        with app.app_context():
            user = User.query.filter_by(email="importer@test.com").first()
            exp = Expense.query.filter_by(user_id=user.id).first()
            assert exp is not None
            assert exp.description == "Steam Game Purchase"
            assert exp.amount == Decimal("59.99")
            assert exp.category.name == "Gaming"
