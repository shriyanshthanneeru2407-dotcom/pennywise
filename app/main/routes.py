"""
app/main/routes.py — Public landing page and root redirect.
"""

from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """
    Landing page for unauthenticated visitors.
    Authenticated users are redirected straight to the dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("index.html", current_month=date.today().strftime("%B %Y"))
