"""
app/dashboard/routes.py — Dashboard and chart API endpoints.

The dashboard page itself is rendered server-side (Jinja2).
Chart data is served via small JSON endpoints that JavaScript calls
on page load to populate Chart.js charts.

All endpoints require authentication (@login_required).
All data is filtered by current_user.id — never expose another user's data.
"""

from datetime import date

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from app.models.expense import Expense
from app.models.recurring import RecurringExpense
from app.models.savings import SavingsGoal
from app.services import analytics

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("")
@login_required
def index():
    """
    Main dashboard page.

    Renders summary cards, recent transactions, and spending insight.
    Chart data is loaded separately via /api/* JSON calls.
    """
    today = date.today()
    year, month = today.year, today.month

    summary = analytics.get_monthly_summary(current_user.id, year, month)
    insights = analytics.get_insights(current_user.id)
    highest = analytics.get_highest_expense(current_user.id, year, month)

    # Recent 8 expenses
    recent = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(8)
        .all()
    )

    # Upcoming recurring expenses (next 30 days)
    upcoming_recurring = (
        RecurringExpense.query
        .filter_by(user_id=current_user.id, active=True)
        .order_by(RecurringExpense.next_due_date)
        .limit(3)
        .all()
    )

    # Savings goals
    savings_goals = (
        SavingsGoal.query
        .filter_by(user_id=current_user.id, status="active")
        .order_by(SavingsGoal.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        summary=summary,
        insights=insights,
        recent=recent,
        highest=highest,
        upcoming_recurring=upcoming_recurring,
        savings_goals=savings_goals,
        today=today,
    )


# --- JSON API endpoints for charts ---
# These are called by dashboard.js on page load.

@dashboard_bp.route("/api/category-spending")
@login_required
def api_category_spending():
    """
    Returns category spending data for the current month.
    Used by the doughnut chart.

    Response format:
        {
            "labels": ["Food", "Transport", ...],
            "data": [12400.0, 4500.0, ...],
            "colors": ["#ef4444", "#3b82f6", ...]
        }
    """
    today = date.today()
    cats = analytics.get_category_totals(current_user.id, today.year, today.month)

    return jsonify({
        "labels": [c["name"] for c in cats],
        "data": [float(c["total"]) for c in cats],
        "colors": [c["color"] for c in cats],
    })


@dashboard_bp.route("/api/daily-spending")
@login_required
def api_daily_spending():
    """
    Returns day-by-day spending for the current month.
    Used by the line chart.

    Response format:
        {
            "labels": ["1", "2", ..., "30"],
            "data": [0.0, 350.0, ...]
        }
    """
    today = date.today()
    daily = analytics.get_daily_spending(current_user.id, today.year, today.month)

    return jsonify({
        "labels": [str(d["day"]) for d in daily],
        "data": [d["total"] for d in daily],
    })


@dashboard_bp.route("/api/monthly-comparison")
@login_required
def api_monthly_comparison():
    """
    Returns 6-month spending history for the bar chart.

    Response format:
        {
            "labels": ["Apr 2026", ..., "Sep 2026"],
            "data": [32000.0, ..., 42350.0]
        }
    """
    months = analytics.get_last_6_months_totals(current_user.id)

    return jsonify({
        "labels": [m["label"] for m in months],
        "data": [m["total"] for m in months],
    })
