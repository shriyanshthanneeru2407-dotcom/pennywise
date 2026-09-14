# app/models/__init__.py
# Importing all models here so Flask-Migrate can discover them
# when it inspects the db object for schema changes.

from .user import User
from .category import Category
from .expense import Expense
from .budget import Budget
from .recurring import RecurringExpense
from .receipt import Receipt

__all__ = ["User", "Category", "Expense", "Budget", "RecurringExpense", "Receipt"]
