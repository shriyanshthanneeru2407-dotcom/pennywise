"""
app/services/export_service.py — Data export helpers.

Generates CSV exports of user expense data.
Security: always receives user_id and filters by it — never exposes
another user's data.
"""

import csv
import io
from app.models.expense import Expense
from app.models.category import Category
from app import db


def generate_expenses_csv(user_id: int) -> str:
    """
    Generate a CSV string of all expenses for the given user.

    Returns:
        A UTF-8 string with CSV content (header + rows).
    """
    expenses = (
        Expense.query
        .filter_by(user_id=user_id)
        .join(Category, Expense.category_id == Category.id)
        .order_by(Expense.expense_date.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Header row
    writer.writerow([
        "Date",
        "Description",
        "Category",
        "Amount",
        "Currency",
        "Payment Method",
        "Notes",
    ])

    # Data rows
    for expense in expenses:
        writer.writerow([
            expense.expense_date.strftime("%Y-%m-%d"),
            expense.description,
            expense.category.name if expense.category else "",
            str(expense.amount),
            expense.currency,
            expense.payment_method,
            expense.notes or "",
        ])

    return output.getvalue()
