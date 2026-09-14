"""
app/insights/routes.py — Spending insights page.

Calls the analytics service to compute observations from real data.
No AI, no external APIs. Pure Python + SQL.
"""

from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services import analytics

insights_bp = Blueprint("insights", __name__)


@insights_bp.route("/")
@insights_bp.route("")
@login_required
def index():
    today = date.today()
    year, month = today.year, today.month

    summary = analytics.get_monthly_summary(current_user.id, year, month)
    categories = analytics.get_category_totals(current_user.id, year, month)
    comparison = analytics.get_monthly_comparison(current_user.id)
    insights = analytics.get_insights(current_user.id)
    highest = analytics.get_highest_expense(current_user.id, year, month)
    monthly_history = analytics.get_last_6_months_totals(current_user.id)

    return render_template(
        "insights/index.html",
        summary=summary,
        categories=categories,
        comparison=comparison,
        insights=insights,
        highest=highest,
        monthly_history=monthly_history,
        today=today,
    )
