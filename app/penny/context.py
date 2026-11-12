"""
app/penny/context.py — Build financial context from the DB for Penny's LLM prompt.

Queries the current user's data (expenses, budgets, savings) and formats
it as a readable text summary that is injected into Penny's system prompt.
"""

from datetime import date, timedelta
from sqlalchemy import func

from app import db
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.category import Category
from app.models.savings import SavingsGoal


def build_financial_context(user) -> str:
    """
    Build a text summary of the user's financial data for the last 90 days.
    Returns a formatted string injected into Penny's system prompt.
    """
    today = date.today()
    ninety_days_ago = today - timedelta(days=90)
    month_start = today.replace(day=1)

    lines = []
    lines.append(f"=== PENNYWISE FINANCIAL CONTEXT FOR {user.name.upper()} ===")
    lines.append(f"Currency: {user.currency} ({user.currency_symbol})")
    lines.append(f"Today's Date: {today.isoformat()}")
    lines.append("")

    # ── Last 90 days expenses by category ──────────────────────────────────
    try:
        category_totals = (
            db.session.query(
                Category.name,
                Category.icon,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("count"),
            )
            .join(Category, Expense.category_id == Category.id)
            .filter(
                Expense.user_id == user.id,
                Expense.transaction_type == "expense",
                Expense.expense_date >= ninety_days_ago,
            )
            .group_by(Category.name, Category.icon)
            .order_by(func.sum(Expense.amount).desc())
            .limit(10)
            .all()
        )

        lines.append("=== TOP SPENDING CATEGORIES (Last 90 days) ===")
        if category_totals:
            for cat in category_totals:
                lines.append(
                    f"  {cat.icon} {cat.name}: {user.currency_symbol}{cat.total:,.2f} ({cat.count} transactions)"
                )
        else:
            lines.append("  No expenses recorded in the last 90 days.")
        lines.append("")
    except Exception:
        pass

    # ── This month totals ──────────────────────────────────────────────────
    try:
        month_expenses = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.user_id == user.id,
                Expense.transaction_type == "expense",
                Expense.expense_date >= month_start,
            )
            .scalar()
            or 0
        )
        month_income = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.user_id == user.id,
                Expense.transaction_type == "income",
                Expense.expense_date >= month_start,
            )
            .scalar()
            or 0
        )
        lines.append("=== THIS MONTH ===")
        lines.append(f"  Total Spent: {user.currency_symbol}{month_expenses:,.2f}")
        lines.append(f"  Total Income: {user.currency_symbol}{month_income:,.2f}")
        lines.append(
            f"  Net Balance: {user.currency_symbol}{month_income - month_expenses:,.2f}"
        )
        lines.append("")
    except Exception:
        pass

    # ── Budgets ────────────────────────────────────────────────────────────
    try:
        budgets = Budget.query.filter_by(user_id=user.id).all()
        if budgets:
            lines.append("=== MONTHLY BUDGETS ===")
            for b in budgets:
                # Spending this month in this category
                spent = (
                    db.session.query(func.sum(Expense.amount))
                    .filter(
                        Expense.user_id == user.id,
                        Expense.category_id == b.category_id,
                        Expense.transaction_type == "expense",
                        Expense.expense_date >= month_start,
                    )
                    .scalar()
                    or 0
                )
                cat = db.session.get(Category, b.category_id)
                cat_name = f"{cat.icon} {cat.name}" if cat else f"Category {b.category_id}"
                pct = (float(spent) / float(b.monthly_limit) * 100) if b.monthly_limit else 0
                status = "⚠️ OVER BUDGET" if spent > b.monthly_limit else ("🟡 Near limit" if pct > 80 else "✅ OK")
                sym = user.currency_symbol
                lines.append(
                    f"  {cat_name}: {sym}{spent:,.2f} / {sym}{b.monthly_limit:,.2f} ({pct:.0f}%) {status}"
                )
            lines.append("")
    except Exception:
        pass

    # ── Savings goals ──────────────────────────────────────────────────────
    try:
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        if goals:
            lines.append("=== SAVINGS GOALS ===")
            for g in goals:
                pct = (float(g.current_amount) / float(g.target_amount) * 100) if g.target_amount else 0
                sym = user.currency_symbol
                lines.append(
                    f"  🏦 {g.title}: {sym}{g.current_amount:,.2f} / {sym}{g.target_amount:,.2f} ({pct:.0f}%)"
                )
            lines.append("")
    except Exception:
        pass

    # ── Recent transactions (last 10) ──────────────────────────────────────
    try:
        recent = (
            Expense.query.filter_by(user_id=user.id)
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .limit(10)
            .all()
        )
        if recent:
            lines.append("=== RECENT TRANSACTIONS (last 10) ===")
            for e in recent:
                prefix = "+" if e.transaction_type == "income" else "−"
                cat = db.session.get(Category, e.category_id)
                cat_name = cat.name if cat else "Unknown"
                lines.append(
                    f"  {e.expense_date}: {prefix}{user.currency_symbol}{e.amount:,.2f} — {e.description} [{cat_name}]"
                )
            lines.append("")
    except Exception:
        pass

    lines.append("=== END OF CONTEXT ===")
    return "\n".join(lines)
