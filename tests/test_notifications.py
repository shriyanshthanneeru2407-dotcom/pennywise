"""
tests/test_notifications.py — Automated tests for in-app notifications.
"""

from app import db
from app.models.notification import Notification
from app.models.user import User
from app.notifications.routes import create_notification


def test_create_notification(app):
    with app.app_context():
        user = User.query.filter_by(email="demo@pennywise.app").first()
        if not user:
            user = User(name="Test User", email="test_notif@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

        notif = create_notification(
            user_id=user.id,
            title="Budget Alert",
            message="80% threshold reached on Food budget.",
            type_="warning",
            link="/budget",
        )

        assert notif.id is not None
        assert notif.title == "Budget Alert"
        assert notif.is_read is False

        # Verify to_dict
        d = notif.to_dict()
        assert d["title"] == "Budget Alert"
        assert d["type"] == "warning"


def test_notifications_route_requires_login(client):
    res = client.get("/notifications/")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]


def test_notifications_lifecycle(client, app):
    with app.app_context():
        user = User.query.filter_by(email="demo@pennywise.app").first()
        if not user:
            user = User(name="Demo User", email="demo@pennywise.app")
            user.set_password("demo1234")
            db.session.add(user)
            db.session.commit()

        # Login
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

        notif = create_notification(
            user_id=user.id,
            title="Milestone Reached",
            message="You reached 50% of your Emergency Fund!",
            type_="success",
        )

        # 1. View notifications page
        res = client.get("/notifications/")
        assert res.status_code == 200
        assert b"Milestone Reached" in res.data

        # 2. View API list
        api_res = client.get("/notifications/api")
        assert api_res.status_code == 200
        data = api_res.get_json()
        assert data["count"] >= 1

        # 3. Mark single as read
        read_res = client.post(f"/notifications/{notif.id}/read", json={})
        assert read_res.status_code == 200
        assert read_res.get_json()["success"] is True

        # Verify database updated
        updated = db.session.get(Notification, notif.id)
        assert updated.is_read is True
