"""
app/models/user.py — User model.

Stores account details and preferences.
Passwords are NEVER stored in plain text — only the Werkzeug hash.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    """
    Represents an application user.

    UserMixin provides Flask-Login helpers:
      is_authenticated, is_active, is_anonymous, get_id()
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # User preferences
    currency = db.Column(db.String(3), nullable=False, default="INR")
    theme = db.Column(db.String(10), nullable=False, default="dark")
    date_format = db.Column(db.String(20), nullable=False, default="%d %b %Y")
    default_budget = db.Column(db.Numeric(12, 2), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    expenses = db.relationship("Expense", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    recurring_expenses = db.relationship("RecurringExpense", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    categories = db.relationship("Category", backref="owner", lazy="dynamic", cascade="all, delete-orphan",
                                 foreign_keys="Category.user_id")

    # --- Password helpers ---

    def set_password(self, password: str) -> None:
        """Hash and store the password. Never store raw password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # --- Display helpers ---

    SUPPORTED_CURRENCIES = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "CAD": "CA$",
        "AUD": "A$",
        "JPY": "¥",
    }

    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol for the user's selected currency."""
        return self.SUPPORTED_CURRENCIES.get(self.currency, self.currency)

    def format_amount(self, amount) -> str:
        """Format a decimal amount with the user's currency symbol."""
        if amount is None:
            return f"{self.currency_symbol}0"
        return f"{self.currency_symbol}{amount:,.2f}"

    def __repr__(self) -> str:
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id: str):
    """
    Flask-Login callback: given a user_id string (from session),
    return the User object or None.
    """
    return db.session.get(User, int(user_id))
