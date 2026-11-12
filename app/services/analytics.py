"""
app/services/analytics.py — Spending analytics engine.

All calculations use actual database data via SQLAlchemy queries.
No hardcoded values. No AI. No external APIs.

Key functions:
  - get_monthly_summary(user, year, month) → totals, category breakdown
  - get_category_totals(user, year, month) → list of (category, amount)
  - get_daily_spending(user, year, month) → day-by-day amounts for line chart
  - get_monthly_comparison(user) → current vs previous month
  - get_insights(user) → list of human-readable observation strings
"""

from decimal import Decimal
from datetime import date, datetime
import calendar

from sqlalchemy import func, extract, or_
from app import db
from app.models.expense import Expense
from app.models.category import Category
from app.models.budget import Budget
from app.models.savings import SavingsGoal, SavingsContribution
from app.models.user import User


def _safe_divide(numerator, denominator, default=Decimal("0")):
    """Division that never raises ZeroDivisionError."""
    if not denominator or denominator == 0:
        return default
    return numerator / denominator


def get_monthly_summary(user_id: int, year: int, month: int) -> dict:
    """
    Return total spending, income, savings, net balance, transaction count,
    and budget breakdown for a given user/year/month.
    """
    # Total expenses (filter by type == 'expense' or None for backwards compatibility)
    exp_result = (
        db.session.query(
            func.coalesce(func.sum(Expense.amount), Decimal("0")).label("total"),
            func.count(Expense.id).label("count"),
        )
        .filter(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
            or_(Expense.transaction_type == "expense", Expense.transaction_type == None),  # noqa: E711
        )
        .one()
    )

    total_expenses = Decimal(str(exp_result.total or "0"))
    expense_count = exp_result.count or 0

    # Total income (filter by type == 'income')
    inc_result = (
        db.session.query(
            func.coalesce(func.sum(Expense.amount), Decimal("0")).label("total"),
            func.count(Expense.id).label("count"),
        )
        .filter(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
            Expense.transaction_type == "income",
        )
        .one()
    )

    total_income = Decimal(str(inc_result.total or "0"))
    income_count = inc_result.count or 0

    count = expense_count + income_count
    net_balance = total_income - total_expenses

    # Total savings in active goals
    total_savings_val = (
        db.session.query(func.coalesce(func.sum(SavingsGoal.current_amount), Decimal("0")))
        .filter(SavingsGoal.user_id == user_id)
        .scalar()
    )
    total_savings = Decimal(str(total_savings_val or "0"))

    # Savings rate = (Income - Expense) / Income * 100
    savings_rate = None
    if total_income > 0:
        savings_rate = float((_safe_divide(net_balance, total_income) * 100).quantize(Decimal("0.1")))

    # Overall Monthly Budget
    budget = Budget.query.filter_by(user_id=user_id, year=year, month=month).first()

    budget_amount = Decimal(str(budget.amount)) if budget else None
    remaining = (budget_amount - total_expenses) if budget_amount is not None else None

    # Budget percentage
    budget_pct = None
    if budget_amount and budget_amount > 0:
        budget_pct = float((_safe_divide(total_expenses, budget_amount) * 100).quantize(Decimal("0.1")))

    # Calculate days elapsed in month to get average daily spend
    today = date.today()
    if year == today.year and month == today.month:
        days_elapsed = today.day
    else:
        days_elapsed = calendar.monthrange(year, month)[1]

    avg_daily = _safe_divide(total_expenses, Decimal(str(days_elapsed)))

    return {
        "total": total_expenses,
        "total_expenses": total_expenses,
        "total_income": total_income,
        "net_balance": net_balance,
        "total_savings": total_savings,
        "savings_rate": savings_rate,
        "count": count,
        "expense_count": expense_count,
        "income_count": income_count,
        "budget": budget_amount,
        "remaining": remaining,
        "budget_pct": budget_pct,
        "avg_daily": avg_daily,
        "year": year,
        "month": month,
        "month_name": date(year, month, 1).strftime("%B"),
    }


def get_category_totals(user_id: int, year: int, month: int) -> list:
    """
    Return a list of dicts: {id, name, icon, color, total, pct} for each
    category that has spending in the given month, sorted by total desc.
    """
    rows = (
        db.session.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Expense.amount).label("total"),
        )
        .join(Expense, Expense.category_id == Category.id)
        .filter(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
            or_(Expense.transaction_type == "expense", Expense.transaction_type == None),  # noqa: E711
        )
        .group_by(Category.id, Category.name, Category.icon, Category.color)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    grand_total = sum(Decimal(str(r.total)) for r in rows)

    result = []
    for row in rows:
        total = Decimal(str(row.total))
        pct = float((_safe_divide(total, grand_total) * 100).quantize(Decimal("0.1")))
        result.append({
            "id": row.id,
            "name": row.name,
            "icon": row.icon,
            "color": row.color,
            "total": total,
            "pct": pct,
        })

    return result


def get_daily_spending(user_id: int, year: int, month: int) -> list:
    """
    Return a list of dicts {day: int, total: Decimal} for each day of
    the month. Days with no spending have total = 0.
    Used for the line chart on the dashboard.
    """
    rows = (
        db.session.query(
            extract("day", Expense.expense_date).label("day"),
            func.sum(Expense.amount).label("total"),
        )
        .filter(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
            or_(Expense.transaction_type == "expense", Expense.transaction_type == None),  # noqa: E711
        )
        .group_by(extract("day", Expense.expense_date))
        .order_by(extract("day", Expense.expense_date))
        .all()
    )

    # Build a full days dict (1 → days_in_month)
    days_in_month = calendar.monthrange(year, month)[1]
    spending_by_day = {int(r.day): Decimal(str(r.total)) for r in rows}

    return [
        {"day": d, "total": float(spending_by_day.get(d, Decimal("0")))}
        for d in range(1, days_in_month + 1)
    ]


def get_monthly_comparison(user_id: int) -> dict:
    """
    Compare current month spending with previous month.
    Returns both totals and percentage change.
    """
    today = date.today()
    curr_year, curr_month = today.year, today.month

    # Previous month
    if curr_month == 1:
        prev_year, prev_month = curr_year - 1, 12
    else:
        prev_year, prev_month = curr_year, curr_month - 1

    def _monthly_total(year, month):
        r = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.user_id == user_id,
                extract("year", Expense.expense_date) == year,
                extract("month", Expense.expense_date) == month,
            )
            .scalar()
        )
        return Decimal(str(r or "0"))

    curr_total = _monthly_total(curr_year, curr_month)
    prev_total = _monthly_total(prev_year, prev_month)

    if prev_total > 0:
        change_pct = float(((_safe_divide(curr_total - prev_total, prev_total)) * 100).quantize(Decimal("0.1")))
    else:
        change_pct = None  # Can't compute meaningful % with zero prev

    return {
        "current_total": curr_total,
        "previous_total": prev_total,
        "change_pct": change_pct,
        "increased": curr_total > prev_total,
        "curr_month_name": date(curr_year, curr_month, 1).strftime("%B"),
        "prev_month_name": date(prev_year, prev_month, 1).strftime("%B"),
    }


def get_last_6_months_totals(user_id: int) -> list:
    """
    Return monthly totals for the last 6 months (for bar chart comparison).
    """
    today = date.today()
    results = []
    for i in range(5, -1, -1):
        # Walk backwards from current month
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        total = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.user_id == user_id,
                extract("year", Expense.expense_date) == year,
                extract("month", Expense.expense_date) == month,
            )
            .scalar()
        )
        results.append({
            "label": date(year, month, 1).strftime("%b %Y"),
            "total": float(Decimal(str(total or "0"))),
            "year": year,
            "month": month,
        })

    return results


def get_highest_expense(user_id: int, year: int, month: int):
    """Return the highest single expense in a given month, or None."""
    return (
        Expense.query
        .filter(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
            or_(Expense.transaction_type == "expense", Expense.transaction_type == None),  # noqa: E711
        )
        .order_by(Expense.amount.desc())
        .first()
    )


def get_insights(user_id: int) -> list:
    """
    Generate a list of human-readable spending observation strings
    from actual data. All edge cases handled: no data, zero prev month,
    no budget, single transaction, etc.

    Returns a list of {"text": str, "type": str} dicts.
    type can be: "info", "success", "warning", "danger"
    """
    today = date.today()
    year, month = today.year, today.month

    user = db.session.get(User, user_id)
    symbol = user.currency_symbol if user else "₹"

    summary = get_monthly_summary(user_id, year, month)
    categories = get_category_totals(user_id, year, month)
    comparison = get_monthly_comparison(user_id)
    highest = get_highest_expense(user_id, year, month)

    observations = []

    # No data at all
    if summary["count"] == 0:
        return [{"text": "Add a few transactions to see spending insights.", "type": "info"}]

    # Savings rate insight
    if summary.get("savings_rate") is not None and summary.get("total_income", Decimal("0")) > 0:
        rate = summary["savings_rate"]
        observations.append({
            "text": f"🌱 Your current savings rate is {rate}% of total income.",
            "type": "success" if rate >= 20 else "info",
        })

    # Largest category
    if categories:
        top = categories[0]
        observations.append({
            "text": f"🏆 {top['name']} is your largest spending category this month ({top['pct']}% of total).",
            "type": "info",
        })

    # Average daily spend
    if summary["avg_daily"] > 0:
        avg = summary["avg_daily"]
        observations.append({
            "text": f"📅 Your average daily spending this month is {_format_amount(avg, symbol)}.",
            "type": "info",
        })

    # Monthly comparison
    if comparison["change_pct"] is not None:
        pct = abs(comparison["change_pct"])
        if comparison["increased"]:
            obs_type = "warning" if pct > 20 else "info"
            observations.append({
                "text": f"📈 Spending increased by {pct}% compared with {comparison['prev_month_name']}.",
                "type": obs_type,
            })
        else:
            observations.append({
                "text": f"📉 Spending decreased by {pct}% compared with {comparison['prev_month_name']}. Well done!",
                "type": "success",
            })
    elif comparison["previous_total"] == 0 and summary["count"] > 0:
        observations.append({
            "text": f"🗓️ This is your first month with recorded expenses.",
            "type": "info",
        })

    # Budget status (50%, 80%, 100% alerts)
    if summary["budget"] and summary["budget_pct"] is not None:
        pct = summary["budget_pct"]
        if pct >= 100:
            over = summary["total"] - summary["budget"]
            observations.append({
                "text": f"🚨 You are {symbol}{over:,.2f} over your monthly budget limit.",
                "type": "danger",
            })
        elif pct >= 80:
            observations.append({
                "text": f"⚠️ 80% threshold reached: You have consumed {pct}% of your monthly budget.",
                "type": "warning",
            })
        elif pct >= 50:
            observations.append({
                "text": f"💡 50% threshold reached: You have consumed {pct}% of your monthly budget.",
                "type": "info",
            })
        else:
            observations.append({
                "text": f"✅ Spending on track: {pct}% of your monthly budget used.",
                "type": "success",
            })
    elif not summary["budget"]:
        observations.append({
            "text": "💰 You haven't set a monthly budget. Set one to track your spending.",
            "type": "info",
        })

    # Highest single expense
    if highest:
        observations.append({
            "text": f"💸 Largest expense this month: {highest.description} — {_format_amount(highest.amount, symbol)}.",
            "type": "info",
        })

    return observations


def _format_amount(amount, symbol: str = "₹") -> str:
    """Amount formatter for insight strings with native currency symbol."""
    return f"{symbol}{float(amount):,.2f}"
