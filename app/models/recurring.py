"""
app/models/recurring.py — Recurring expense model.

Tracks expenses that happen on a regular schedule (rent, subscriptions, etc.).
This is for TRACKING purposes only — it does not automatically create expense
records. The user is shown upcoming recurring items and can log them manually.
"""

from datetime import datetime, timezone
from app import db


FREQUENCIES = ["Weekly", "Monthly", "Yearly"]


class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")

    frequency = db.Column(db.String(10), nullable=False, default="Monthly")  # Weekly/Monthly/Yearly
    next_due_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default="Other")

    # Active flag — users can pause recurring items without deleting them
    active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<RecurringExpense {self.description} {self.frequency}>"
