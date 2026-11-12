"""
seed.py — Development-only seed script.

Populates the database with:
  1. Default system categories (if not already present)
  2. A demo user account
  3. Realistic sample expenses for the demo user

IMPORTANT: Never run this in production. It creates demo data only.

Usage:
    flask --app app shell < seed.py
    # or:
    python seed.py
"""

import os
import sys
from decimal import Decimal
from datetime import date, timedelta
import random

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.category import Category, DEFAULT_CATEGORIES
from app.models.expense import Expense, PAYMENT_METHODS
from app.models.budget import Budget
from app.models.recurring import RecurringExpense
from app.models.savings import SavingsGoal, SavingsContribution


def seed():
    app = create_app("development")

    with app.app_context():
        print("🌱 Seeding database...")
        db.create_all()

        # --- 1. Seed default categories ---
        print("  → Creating system categories...")
        for cat_data in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(user_id=None, name=cat_data["name"]).first()
            if not existing:
                cat = Category(user_id=None, **cat_data)
                db.session.add(cat)

        db.session.commit()
        print(f"     ✓ {len(DEFAULT_CATEGORIES)} categories ready")

        # --- 2. Create demo user ---
        demo_email = "demo@pennywise.app"
        user = User.query.filter_by(email=demo_email).first()

        if not user:
            print("  → Creating demo user...")
            user = User(
                name="PennyWise Demo",
                email=demo_email,
                currency="INR",
                theme="dark",
            )
            user.set_password("demo1234")
            db.session.add(user)
            db.session.commit()
            print(f"     ✓ Demo user: {demo_email} / demo1234")
        else:
            print(f"     ✓ Demo user already exists: {demo_email}")

        # --- 3. Set a budget for the current month ---
        today = date.today()
        budget = Budget.query.filter_by(
            user_id=user.id, year=today.year, month=today.month
        ).first()

        if not budget:
            budget = Budget(
                user_id=user.id,
                year=today.year,
                month=today.month,
                amount=Decimal("50000"),
                currency="INR",
            )
            db.session.add(budget)
            db.session.commit()
            print("     ✓ Monthly budget set: ₹50,000")

        # --- 4. Seed sample expenses (current month + last month) ---
        cats = {c.name: c for c in Category.query.filter_by(user_id=None).all()}

        def add_expense(desc, cat_name, amount, days_ago=0, payment="UPI", notes=None):
            expense_date = today - timedelta(days=days_ago)
            # Skip if already exists (re-run safe)
            existing = Expense.query.filter_by(
                user_id=user.id,
                description=desc,
                expense_date=expense_date,
            ).first()
            if existing:
                return
            e = Expense(
                user_id=user.id,
                category_id=cats[cat_name].id,
                amount=Decimal(str(amount)),
                currency="INR",
                description=desc,
                expense_date=expense_date,
                payment_method=payment,
                notes=notes,
            )
            db.session.add(e)

        print("  → Creating sample expenses (current month)...")

        # Current month
        add_expense("Lunch - South Indian", "Food", 350, 0, "UPI")
        add_expense("Uber to office", "Transport", 280, 0, "UPI")
        add_expense("Groceries - Big Bazaar", "Groceries", 1850, 1, "Debit Card")
        add_expense("Movie - Interstellar re-release", "Entertainment", 600, 1, "Credit Card")
        add_expense("Dinner - Family restaurant", "Food", 1200, 2, "Credit Card", "Family dinner")
        add_expense("Auto fare", "Transport", 120, 2, "Cash")
        add_expense("Electricity bill", "Bills", 4500, 3, "UPI")
        add_expense("Amazon order - books", "Shopping", 1299, 3, "Credit Card")
        add_expense("Pharmacy", "Health", 450, 4, "Cash")
        add_expense("Coffee shop", "Food", 280, 4, "UPI")
        add_expense("Gym membership", "Health", 2000, 5, "UPI")
        add_expense("Vegetables - local market", "Groceries", 380, 5, "Cash")
        add_expense("Netflix subscription", "Entertainment", 649, 6, "Credit Card")
        add_expense("Petrol", "Transport", 1200, 6, "Cash")
        add_expense("Online course - Python", "Education", 2499, 7, "Credit Card")
        add_expense("Breakfast - cafe", "Food", 320, 7, "UPI")
        add_expense("Grocery run - Reliance Fresh", "Groceries", 1540, 8, "Debit Card")
        add_expense("Bus pass", "Transport", 500, 9, "Cash")
        add_expense("Mobile recharge", "Bills", 299, 9, "UPI")
        add_expense("Flight ticket - Mumbai", "Travel", 8500, 10, "Credit Card", "Work trip")
        add_expense("Hotel - Mumbai 2 nights", "Travel", 6800, 10, "Credit Card", "Work trip")
        add_expense("Swiggy order", "Food", 520, 11, "UPI")
        add_expense("Zomato order", "Food", 680, 12, "UPI")
        add_expense("Clothing - Myntra", "Shopping", 2499, 12, "Credit Card")
        add_expense("Doctor consultation", "Health", 800, 13, "Cash")
        add_expense("Medicine", "Health", 350, 13, "Cash")
        add_expense("Internet bill", "Bills", 999, 14, "UPI")
        add_expense("Milk & dairy", "Groceries", 420, 14, "Cash")

        # Last month expenses
        last_month_offset = 32
        add_expense("Lunch - Biriyani", "Food", 420, last_month_offset, "UPI")
        add_expense("Auto fare", "Transport", 90, last_month_offset, "Cash")
        add_expense("Groceries", "Groceries", 2100, last_month_offset + 2, "Debit Card")
        add_expense("Electricity bill", "Bills", 4200, last_month_offset + 3, "UPI")
        add_expense("Movie tickets", "Entertainment", 800, last_month_offset + 5, "Credit Card")
        add_expense("Medicines", "Health", 560, last_month_offset + 7, "Cash")
        add_expense("Clothes shopping", "Shopping", 3200, last_month_offset + 8, "Credit Card")
        add_expense("Dining out", "Food", 1800, last_month_offset + 10, "UPI")
        add_expense("Bus fare", "Transport", 240, last_month_offset + 12, "Cash")
        add_expense("Swiggy", "Food", 450, last_month_offset + 15, "UPI")
        add_expense("Books", "Education", 850, last_month_offset + 16, "Credit Card")
        add_expense("Mobile bill", "Bills", 499, last_month_offset + 18, "UPI")

        db.session.commit()
        print("     ✓ Sample expenses created")

        # Seed income transactions
        if "Salary" in cats:
            add_expense("Monthly Tech Salary", "Salary", 85000, 2, "Bank Transfer", notes="Direct deposit")
        if "Freelance" in cats:
            add_expense("Web Design Project", "Freelance", 25000, 10, "Bank Transfer", notes="Client milestone 2")

        # --- 5. Seed savings goals ---
        print("  → Creating savings goals...")
        if not SavingsGoal.query.filter_by(user_id=user.id).first():
            g1 = SavingsGoal(
                user_id=user.id,
                title="🛡️ Emergency Vault",
                target_amount=Decimal("100000.00"),
                current_amount=Decimal("45000.00"),
                category="Emergency Fund",
                target_date=today + timedelta(days=180),
            )
            g2 = SavingsGoal(
                user_id=user.id,
                title="✈️ Japan Vacation",
                target_amount=Decimal("150000.00"),
                current_amount=Decimal("65000.00"),
                category="Vacation",
                target_date=today + timedelta(days=240),
            )
            db.session.add_all([g1, g2])
            db.session.commit()
            print("     ✓ Savings goals created")

        # --- 6. Seed recurring expenses ---
        print("  → Creating recurring expenses...")

        def add_recurring(desc, cat_name, amount, frequency, days_until_due=28, payment="UPI"):
            existing = RecurringExpense.query.filter_by(
                user_id=user.id, description=desc
            ).first()
            if existing:
                return
            r = RecurringExpense(
                user_id=user.id,
                category_id=cats[cat_name].id,
                description=desc,
                amount=Decimal(str(amount)),
                currency="INR",
                frequency=frequency,
                next_due_date=today + timedelta(days=days_until_due),
                payment_method=payment,
                active=True,
            )
            db.session.add(r)

        add_recurring("Netflix", "Entertainment", 649, "Monthly", 14, "Credit Card")
        add_recurring("Gym membership", "Health", 2000, "Monthly", 20, "UPI")
        add_recurring("Internet bill", "Bills", 999, "Monthly", 16, "UPI")
        add_recurring("Electricity bill", "Bills", 4500, "Monthly", 27, "UPI")

        db.session.commit()
        print("     ✓ Recurring expenses created")

        print("\n✅ Seed complete!")
        print(f"   Demo login: {demo_email}")
        print("   Password:   demo1234")


if __name__ == "__main__":
    seed()
