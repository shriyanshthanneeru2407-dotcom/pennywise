"""
tests/test_savings.py — Unit tests for savings goals and contributions.
"""

from decimal import Decimal
from app import db
from app.models.user import User
from app.models.savings import SavingsGoal, SavingsContribution
from tests.conftest import login


class TestSavingsGoals:
    def _login_user(self, client, app, email="savings_user@test.com"):
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name="Savings User", email=email, currency="INR")
                u.set_password("password123")
                db.session.add(u)
                db.session.commit()
            uid = u.id
        login(client, email, "password123")
        return uid

    def test_create_savings_goal(self, client, app):
        """User can create a savings goal with target and initial amount."""
        user_id = self._login_user(client, app, "goal_creator@test.com")

        resp = client.post("/savings/new", data={
            "title": "Emergency Fund",
            "target_amount": "50000.00",
            "initial_amount": "10000.00",
            "category": "Emergency Fund",
            "target_date": "2026-12-31",
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert b"Emergency Fund" in resp.data

        with app.app_context():
            goal = SavingsGoal.query.filter_by(user_id=user_id, title="Emergency Fund").first()
            assert goal is not None
            assert goal.target_amount == Decimal("50000.00")
            assert goal.current_amount == Decimal("10000.00")
            assert goal.progress_pct == 20.0
            assert goal.remaining_amount == Decimal("40000.00")
            assert not goal.is_completed

    def test_contribute_to_savings_goal(self, client, app):
        """User can make deposits/contributions to their goal."""
        user_id = self._login_user(client, app, "goal_contrib@test.com")

        with app.app_context():
            goal = SavingsGoal(
                user_id=user_id,
                title="New Laptop",
                target_amount=Decimal("80000.00"),
                current_amount=Decimal("20000.00"),
            )
            db.session.add(goal)
            db.session.commit()
            goal_id = goal.id

        resp = client.post(f"/savings/{goal_id}/contribute", data={
            "amount": "60000.00",
            "notes": "Salary bonus",
        }, follow_redirects=True)

        assert resp.status_code == 200

        with app.app_context():
            updated_goal = db.session.get(SavingsGoal, goal_id)
            assert updated_goal.current_amount == Decimal("80000.00")
            assert updated_goal.progress_pct == 100.0
            assert updated_goal.is_completed
            assert updated_goal.status == "completed"

            # Check contribution record
            contrib = SavingsContribution.query.filter_by(goal_id=goal_id).first()
            assert contrib is not None
            assert contrib.amount == Decimal("60000.00")
            assert contrib.notes == "Salary bonus"

    def test_delete_savings_goal(self, client, app):
        """User can delete their own savings goal."""
        user_id = self._login_user(client, app, "goal_deleter@test.com")

        with app.app_context():
            goal = SavingsGoal(
                user_id=user_id,
                title="Trip",
                target_amount=Decimal("15000.00"),
            )
            db.session.add(goal)
            db.session.commit()
            goal_id = goal.id

        resp = client.post(f"/savings/{goal_id}/delete", follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            assert db.session.get(SavingsGoal, goal_id) is None
