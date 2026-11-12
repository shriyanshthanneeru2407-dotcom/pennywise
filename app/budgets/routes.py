"""
app/budgets/routes.py — Monthly and category budget management.

Users set a budget per month or per category.
The budget page shows:
  - Current month overall budget vs spending
  - Progress bar with status color and 50%, 80%, 100% threshold alerts
  - Category-specific budgets with real-time utilization
  - Form to set or update category spending limits

All reads/writes are scoped to current_user.id.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models.budget import Budget, CategoryBudget
from app.models.category import Category
from app.services import analytics

budgets_bp = Blueprint("budgets", __name__)


def _compute_threshold(pct: float) -> dict:
    """Return badge color, status text, and alert flag based on budget percent used."""
    if pct >= 100:
        return {
            "level": "danger",
            "label": "100% Budget Exceeded",
            "badge_class": "badge-danger",
            "color": "var(--danger)",
            "alert": True,
        }
    elif pct >= 80:
        return {
            "level": "warning",
            "label": "80% Threshold Reached",
            "badge_class": "badge-warning",
            "color": "var(--warning)",
            "alert": True,
        }
    elif pct >= 50:
        return {
            "level": "info",
            "label": "50% Budget Consumed",
            "badge_class": "badge-info",
            "color": "var(--accent)",
            "alert": False,
        }
    else:
        return {
            "level": "success",
            "label": "On Track",
            "badge_class": "badge-success",
            "color": "var(--success)",
            "alert": False,
        }


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
    category_totals = analytics.get_category_totals(current_user.id, year, month)
    monthly_history = analytics.get_last_6_months_totals(current_user.id)

    # Calculate overall threshold alert
    overall_threshold = None
    if summary.get("budget_pct") is not None:
        overall_threshold = _compute_threshold(summary["budget_pct"])

    # Load category budgets for this month
    cat_budgets = CategoryBudget.query.filter_by(
        user_id=current_user.id, year=year, month=month
    ).all()

    # Build category totals lookup {category_id: total_spent}
    cat_spent_map = {item["id"]: item["total"] for item in category_totals}

    category_budget_list = []
    for cb in cat_budgets:
        spent = cat_spent_map.get(cb.category_id, Decimal("0.00"))
        remaining = cb.amount - spent
        pct = float((spent / cb.amount) * 100) if cb.amount > 0 else 0.0
        pct_clamped = min(pct, 100.0)
        threshold = _compute_threshold(pct)
        category_budget_list.append({
            "id": cb.id,
            "category": cb.category,
            "category_id": cb.category_id,
            "budget_amount": cb.amount,
            "spent": spent,
            "remaining": remaining,
            "pct": round(pct, 1),
            "pct_clamped": round(pct_clamped, 1),
            "threshold": threshold,
        })

    # Available expense categories for setting a new category budget
    configured_cat_ids = {cb.category_id for cb in cat_budgets}
    available_categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id.is_(None))
    ).filter_by(category_type="expense").all()

    return render_template(
        "budgets/index.html",
        budget=budget,
        summary=summary,
        categories=category_totals,
        category_budgets=category_budget_list,
        available_categories=available_categories,
        configured_cat_ids=configured_cat_ids,
        overall_threshold=overall_threshold,
        monthly_history=monthly_history,
        today=today,
    )


@budgets_bp.route("/set", methods=["POST"])
@login_required
def set_budget():
    """
    Create or update the overall budget for the current month.
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
    flash("Monthly budget updated successfully.", "success")
    return redirect(url_for("budgets.index"))


@budgets_bp.route("/category/set", methods=["POST"])
@login_required
def set_category_budget():
    """
    Create or update a category-specific budget for the current month.
    """
    today = date.today()
    year, month = today.year, today.month

    category_id_str = request.form.get("category_id", "").strip()
    amount_str = request.form.get("amount", "").strip()

    try:
        category_id = int(category_id_str)
        category = db.session.get(Category, category_id)
        if not category or (category.user_id not in (None, current_user.id)):
            flash("Invalid category selected.", "danger")
            return redirect(url_for("budgets.index"))
    except (ValueError, TypeError):
        flash("Invalid category selected.", "danger")
        return redirect(url_for("budgets.index"))

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            flash("Category budget must be greater than zero.", "danger")
            return redirect(url_for("budgets.index"))
        if amount > Decimal("99999999.99"):
            flash("Amount is unreasonably large.", "danger")
            return redirect(url_for("budgets.index"))
    except (InvalidOperation, ValueError):
        flash("Please enter a valid numeric amount.", "danger")
        return redirect(url_for("budgets.index"))

    cat_budget = CategoryBudget.query.filter_by(
        user_id=current_user.id, category_id=category_id, year=year, month=month
    ).first()

    if cat_budget:
        cat_budget.amount = amount
    else:
        cat_budget = CategoryBudget(
            user_id=current_user.id,
            category_id=category_id,
            year=year,
            month=month,
            amount=amount,
        )
        db.session.add(cat_budget)

    db.session.commit()
    flash(f"Budget for {category.name} set to {current_user.currency_symbol}{amount:,.2f}.", "success")
    return redirect(url_for("budgets.index"))


@budgets_bp.route("/category/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete_category_budget(budget_id):
    """Remove a category budget cap."""
    cat_budget = CategoryBudget.query.filter_by(
        id=budget_id, user_id=current_user.id
    ).first_or_404()

    category_name = cat_budget.category.name if cat_budget.category else "Category"
    db.session.delete(cat_budget)
    db.session.commit()

    flash(f"Budget limit for {category_name} removed.", "info")
    return redirect(url_for("budgets.index"))
