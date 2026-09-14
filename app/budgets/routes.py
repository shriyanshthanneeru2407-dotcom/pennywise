"""
app/budgets/routes.py — Monthly budget management.

Users set a budget per month. This is stored in the budgets table.
The budget page shows:
  - Current month budget vs spending
  - Progress bar with status color
  - Category-level breakdown

All reads/writes are scoped to current_user.id.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models.budget import Budget
from app.services import analytics

budgets_bp = Blueprint("budgets", __name__)


@budgets_bp.route("/")
@budgets_bp.route("")
@login_required
def index():
    """Show budget overview for current month and previous months."""
    today = date.today()
    year, month = today.year, today.month

    budget = Budget.query.filter_by(
        user_id=current_user.id, year=year, month=month
    ).first()

    summary = analytics.get_monthly_summary(current_user.id, year, month)
    categories = analytics.get_category_totals(current_user.id, year, month)
    monthly_history = analytics.get_last_6_months_totals(current_user.id)

    return render_template(
        "budgets/index.html",
        budget=budget,
        summary=summary,
        categories=categories,
        monthly_history=monthly_history,
        today=today,
    )


@budgets_bp.route("/set", methods=["POST"])
@login_required
def set_budget():
    """
    Create or update the budget for the current month.
    Uses INSERT or UPDATE (upsert pattern via SQLAlchemy).
    """
    today = date.today()
    year, month = today.year, today.month

    amount_str = request.form.get("amount", "").strip()
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            flash("Budget amount must be greater than zero.", "danger")
            return redirect(url_for("budgets.index"))
        if amount > Decimal("99999999.99"):
            flash("Budget amount is unreasonably large.", "danger")
            return redirect(url_for("budgets.index"))
    except (InvalidOperation, ValueError):
        flash("Please enter a valid budget amount.", "danger")
        return redirect(url_for("budgets.index"))

    # Upsert: update if exists, else create
    budget = Budget.query.filter_by(
        user_id=current_user.id, year=year, month=month
    ).first()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(
            user_id=current_user.id,
            year=year,
            month=month,
            amount=amount,
            currency=current_user.currency,
        )
        db.session.add(budget)

    db.session.commit()
    flash("Budget updated.", "success")
    return redirect(url_for("budgets.index"))
