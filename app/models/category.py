"""
app/models/category.py — Expense Category model.

Categories can be:
  - System defaults (user_id = NULL): shared across all users
  - User-created (user_id = <id>): private to that user

When querying categories for a user, we always fetch:
    WHERE user_id IS NULL OR user_id = current_user.id
"""

from datetime import datetime, timezone
from app import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    # NULL means this is a system/default category visible to all users.
    # Non-NULL means it belongs to a specific user.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), nullable=False, default="📦")  # Emoji icon
    color = db.Column(db.String(7), nullable=False, default="#6366f1")  # Hex color for charts

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship back to expenses
    expenses = db.relationship("Expense", backref="category", lazy="dynamic")
    recurring_expenses = db.relationship("RecurringExpense", backref="category", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


# Default system categories seeded into the database
DEFAULT_CATEGORIES = [
    {"name": "Food",          "icon": "🍽️",  "color": "#ef4444"},
    {"name": "Groceries",     "icon": "🛒",  "color": "#f97316"},
    {"name": "Transport",     "icon": "🚗",  "color": "#3b82f6"},
    {"name": "Shopping",      "icon": "🛍️",  "color": "#8b5cf6"},
    {"name": "Bills",         "icon": "📄",  "color": "#6b7280"},
    {"name": "Entertainment", "icon": "🎬",  "color": "#ec4899"},
    {"name": "Health",        "icon": "💊",  "color": "#10b981"},
    {"name": "Education",     "icon": "📚",  "color": "#0ea5e9"},
    {"name": "Travel",        "icon": "✈️",  "color": "#f59e0b"},
    {"name": "Rent",          "icon": "🏠",  "color": "#84cc16"},
    {"name": "Utilities",     "icon": "💡",  "color": "#14b8a6"},
    {"name": "Other",         "icon": "📦",  "color": "#9ca3af"},
]
