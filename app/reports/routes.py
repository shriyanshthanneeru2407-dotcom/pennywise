"""
app/reports/routes.py — Financial reports, annual summaries, and CSV exports.
"""

from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, Response, request
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app import db
from app.models.expense import Expense
from app.models.category import Category
from app.services import analytics
from app.services.export_service import generate_expenses_csv

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@reports_bp.route("")
@login_required
def index():
    today = date.today()
    selected_year = request.args.get("year", today.year, type=int)

    # Calculate 12-month summary for the selected year
    months_data = []
    total_annual_income = Decimal("0.00")
    total_annual_expense = Decimal("0.00")

    for m in range(1, 13):
        summary = analytics.get_monthly_summary(current_user.id, selected_year, m)
        total_annual_income += summary["total_income"]
        total_annual_expense += summary["total_expenses"]
        months_data.append({
            "month_num": m,
            "month_name": date(selected_year, m, 1).strftime("%b"),
            "income": summary["total_income"],
            "expense": summary["total_expenses"],
            "balance": summary["net_balance"],
            "count": summary["count"],
        })

    net_annual_balance = total_annual_income - total_annual_expense
    annual_savings_rate = None
    if total_annual_income > 0:
        annual_savings_rate = round(float((net_annual_balance / total_annual_income) * 100), 1)

    # Top spending categories for this year
    category_totals = (
        db.session.query(
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Expense.amount).label("total"),
        )
        .join(Expense, Expense.category_id == Category.id)
        .filter(
            Expense.user_id == current_user.id,
            extract("year", Expense.expense_date) == selected_year,
            Expense.transaction_type == "expense",
        )
        .group_by(Category.id, Category.name, Category.icon, Category.color)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    return render_template(
        "reports/index.html",
        selected_year=selected_year,
        months_data=months_data,
        total_annual_income=total_annual_income,
        total_annual_expense=total_annual_expense,
        net_annual_balance=net_annual_balance,
        annual_savings_rate=annual_savings_rate,
        category_totals=category_totals,
        today=today,
    )


@reports_bp.route("/export.csv")
@login_required
def export_csv():
    """Download clean, sanitized CSV export of all user transactions."""
    csv_data = generate_expenses_csv(current_user.id)
    filename = f"pennywise_transactions_{date.today().isoformat()}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
