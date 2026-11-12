# app/models/__init__.py
# Importing all models here so Flask-Migrate can discover them
# when it inspects the db object for schema changes.

from .user import User
from .category import Category
from .expense import Expense
from .budget import Budget, CategoryBudget
from .recurring import RecurringExpense
from .receipt import Receipt
from .savings import SavingsGoal, SavingsContribution

__all__ = ["User", "Category", "Expense", "Budget", "CategoryBudget", "RecurringExpense", "Receipt", "SavingsGoal", "SavingsContribution"]
