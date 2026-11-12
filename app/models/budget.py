"""
app/models/budget.py — Monthly budget model.

A budget is defined per user per month (year + month).
The unique constraint prevents accidentally creating duplicate budgets.
"""

from datetime import datetime, timezone
from app import db


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1–12

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Ensure exactly one overall budget per user per month
    __table_args__ = (
        db.UniqueConstraint("user_id", "year", "month", name="uq_budget_user_month"),
        db.Index("ix_budgets_user_year_month", "user_id", "year", "month"),
    )

    def __repr__(self) -> str:
        return f"<Budget user={self.user_id} {self.year}-{self.month:02d} {self.amount}>"


class CategoryBudget(db.Model):
    __tablename__ = "category_budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)

    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)

    amount = db.Column(db.Numeric(12, 2), nullable=False)

    category = db.relationship("Category")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "year", "month", name="uq_category_budget_user_month"),
        db.Index("ix_cat_budgets_user_year_month", "user_id", "year", "month"),
    )

    def __repr__(self) -> str:
        return f"<CategoryBudget user={self.user_id} cat={self.category_id} {self.year}-{self.month:02d} {self.amount}>"
