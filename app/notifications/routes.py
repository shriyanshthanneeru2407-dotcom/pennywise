"""
app/notifications/routes.py — In-app notification routes and services.
"""

from flask import Blueprint, jsonify, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification

notifications_bp = Blueprint("notifications", __name__)


def create_notification(user_id: int, title: str, message: str, type_: str = "info", link: str = None):
    """Utility to create an in-app notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type_,
        link=link,
    )
    db.session.add(notif)
    db.session.commit()
    return notif


@notifications_bp.route("/")
@login_required
def index():
    """List all notifications for the current user."""
    notifications = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("notifications/index.html", notifications=notifications)


@notifications_bp.route("/api")
@login_required
def api_list():
    """Return JSON list of recent unread notifications."""
    unread = (
        Notification.query
        .filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    return jsonify({
        "count": len(unread),
        "notifications": [n.to_dict() for n in unread],
    })


@notifications_bp.route("/<int:id>/read", methods=["POST"])
@login_required
def mark_read(id: int):
    """Mark a single notification as read."""
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    return redirect(request.referrer or url_for("notifications.index"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    """Mark all notifications for current user as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("All notifications marked as read.", "success")
    return redirect(request.referrer or url_for("notifications.index"))
