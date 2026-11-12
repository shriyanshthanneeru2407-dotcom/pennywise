"""
app/models/expense.py — Expense model.

IMPORTANT: Amount uses NUMERIC(12, 2) — never Float.
Using float for money causes precision errors like ₹100.10 → 100.09999999.
SQLAlchemy's Numeric type maps to PostgreSQL NUMERIC and Python Decimal.
"""

from datetime import datetime, timezone
from app import db


# Valid payment methods (used in validation + form choices)
PAYMENT_METHODS = [
    "Cash",
    "Debit Card",
    "Credit Card",
    "Bank Transfer",
    "UPI",
    "Other",
]


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys — cascade delete so removing a user removes their expenses
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)

    # Money: NUMERIC(12, 2) prevents floating-point errors
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    transaction_type = db.Column(db.String(10), nullable=False, default="expense")  # 'expense' or 'income'

    description = db.Column(db.String(200), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, index=True)
    payment_method = db.Column(db.String(20), nullable=False, default="Cash")
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # One-to-one relationship with receipt (optional)
    receipt = db.relationship("Receipt", backref="expense", uselist=False, cascade="all, delete-orphan")

    # Compound index for the most common dashboard query:
    # "get all expenses for user X in month Y"
    __table_args__ = (
        db.Index("ix_expenses_user_date", "user_id", "expense_date"),
    )

    def __repr__(self) -> str:
        return f"<Expense {self.description} {self.amount}>"
