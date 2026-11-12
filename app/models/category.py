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
    category_type = db.Column(db.String(10), nullable=False, default="expense")  # 'expense' or 'income'
    icon = db.Column(db.String(10), nullable=False, default="📦")  # Emoji icon
    color = db.Column(db.String(7), nullable=False, default="#6366f1")  # Hex color for charts

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship back to expenses
    expenses = db.relationship("Expense", backref="category", lazy="dynamic")
    recurring_expenses = db.relationship("RecurringExpense", backref="category", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.category_type})>"


# Default system categories seeded into the database
DEFAULT_CATEGORIES = [
    # Expenses
    {"name": "Food",          "icon": "🍽️",  "color": "#ef4444", "category_type": "expense"},
    {"name": "Groceries",     "icon": "🛒",  "color": "#f97316", "category_type": "expense"},
    {"name": "Shopping",      "icon": "🛍️",  "color": "#8b5cf6", "category_type": "expense"},
    {"name": "Transportation", "icon": "🚗",  "color": "#3b82f6", "category_type": "expense"},
    {"name": "Healthcare",    "icon": "💊",  "color": "#10b981", "category_type": "expense"},
    {"name": "Entertainment", "icon": "🎬",  "color": "#ec4899", "category_type": "expense"},
    {"name": "Education",     "icon": "📚",  "color": "#0ea5e9", "category_type": "expense"},
    {"name": "Rent",          "icon": "🏠",  "color": "#84cc16", "category_type": "expense"},
    {"name": "Utilities",     "icon": "💡",  "color": "#14b8a6", "category_type": "expense"},
    {"name": "Travel",        "icon": "✈️",  "color": "#f59e0b", "category_type": "expense"},
    {"name": "Other Expense", "icon": "📦",  "color": "#9ca3af", "category_type": "expense"},
    # Income
    {"name": "Salary",         "icon": "💼",  "color": "#00e676", "category_type": "income"},
    {"name": "Freelance",      "icon": "💻",  "color": "#00b0ff", "category_type": "income"},
    {"name": "Business",       "icon": "🏢",  "color": "#ffd600", "category_type": "income"},
    {"name": "Investments",    "icon": "📈",  "color": "#76ff03", "category_type": "income"},
    {"name": "Other Income",   "icon": "💵",  "color": "#a7ffeb", "category_type": "income"},
]
