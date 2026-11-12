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

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.category import Category, DEFAULT_CATEGORIES  # noqa: E402
from app.models.expense import Expense  # noqa: E402
from app.models.budget import Budget  # noqa: E402
from app.models.recurring import RecurringExpense  # noqa: E402
from app.models.savings import SavingsGoal  # noqa: E402
from app.models.notification import Notification  # noqa: E402


def seed():
    app = create_app("development")

    with app.app_context():
        print("🌱 Seeding database...")
        db.create_all()

        # --- 1. Seed default categories ---
        print("  → Creating system categories...")
        for cat_data in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(
                user_id=None,
                name=cat_data["name"],
            ).first()
            if not existing:
                cat = Category(user_id=None, **cat_data)
                db.session.add(cat)
        db.session.commit()
        print("     ✓ Categories created")

        # --- 2. Seed demo user ---
        print("  → Creating demo user...")
        demo_email = "demo@pennywise.app"
        user = User.query.filter_by(email=demo_email).first()
        if not user:
            user = User(
                name="Demo User",
                email=demo_email,
                currency="INR",
                email_verified=True,
            )
            user.set_password("demo1234")
            db.session.add(user)
            db.session.commit()
            print(f"     ✓ Created user {demo_email}")
        else:
            print(f"     ℹ User {demo_email} already exists")

        # --- 3. Seed monthly budget ---
        print("  → Creating monthly budget...")
        today = date.today()
        existing_budget = Budget.query.filter_by(
            user_id=user.id,
            year=today.year,
            month=today.month,
        ).first()
        if not existing_budget:
            budget = Budget(
                user_id=user.id,
                year=today.year,
                month=today.month,
                amount=Decimal("50000.00"),
                currency="INR",
            )
            db.session.add(budget)
            db.session.commit()
            print(f"     ✓ Budget set to ₹50,000 for {today.strftime('%B %Y')}")
        else:
            print("     ℹ Budget already exists")

        # --- 4. Seed sample expenses (current month + last month) ---
        cats = {c.name: c for c in Category.query.filter_by(user_id=None).all()}

        print("  → Creating sample expenses (current month)...")

        # Helper to get cat or fallback
        def get_cat(name):
            return cats.get(name) or cats.get("Other Expense") or list(cats.values())[0]

        def add_expense(desc, cat_name, amount, days_ago, payment, notes=None, tx_type=None):
            expense_date = today - timedelta(days=days_ago)
            target_cat = get_cat(cat_name)
            t_type = tx_type or target_cat.category_type
            e = Expense(
                user_id=user.id,
                category_id=target_cat.id,
                transaction_type=t_type,
                amount=Decimal(str(amount)),
                currency="INR",
                description=desc,
                expense_date=expense_date,
                payment_method=payment,
                notes=notes,
            )
            db.session.add(e)

        # Current month expenses
        add_expense("Lunch - South Indian", "Food", 350, 0, "UPI")
        add_expense("Uber to office", "Transportation", 280, 0, "UPI")
        add_expense("Groceries - Big Bazaar", "Groceries", 1850, 1, "Debit Card")
        add_expense("Movie - Interstellar re-release", "Entertainment", 600, 1, "Credit Card")
        add_expense("Dinner - Family restaurant", "Food", 1200, 2, "Credit Card", "Family dinner")
        add_expense("Auto fare", "Transportation", 120, 2, "Cash")
        add_expense("Electricity bill", "Utilities", 4500, 3, "UPI")
        add_expense("Amazon order - books", "Shopping", 1299, 3, "Credit Card")
        add_expense("Pharmacy", "Healthcare", 450, 4, "Cash")
        add_expense("Coffee shop", "Food", 280, 4, "UPI")
        add_expense("Gym membership", "Healthcare", 2000, 5, "UPI")
        add_expense("Vegetables - local market", "Groceries", 380, 5, "Cash")
        add_expense("Netflix subscription", "Entertainment", 649, 6, "Credit Card")
        add_expense("Petrol", "Transportation", 1200, 6, "Cash")
        add_expense("Online course - Python", "Education", 2499, 7, "Credit Card")
        add_expense("Breakfast - cafe", "Food", 320, 7, "UPI")
        add_expense("Grocery run - Reliance Fresh", "Groceries", 1540, 8, "Debit Card")
        add_expense("Bus pass", "Transportation", 500, 9, "Cash")
        add_expense("Mobile recharge", "Utilities", 299, 9, "UPI")
        add_expense("Flight ticket - Mumbai", "Travel", 8500, 10, "Credit Card", "Work trip")
        add_expense("Hotel - Mumbai 2 nights", "Travel", 6800, 10, "Credit Card", "Work trip")
        add_expense("Swiggy order", "Food", 520, 11, "UPI")
        add_expense("Zomato order", "Food", 680, 12, "UPI")
        add_expense("Clothing - Myntra", "Shopping", 2499, 12, "Credit Card")
        add_expense("Doctor consultation", "Healthcare", 800, 13, "Cash")
        add_expense("Medicine", "Healthcare", 350, 13, "Cash")
        add_expense("Internet bill", "Utilities", 999, 14, "UPI")
        add_expense("Milk & dairy", "Groceries", 420, 14, "Cash")

        # Last month expenses
        last_month_offset = 32
        add_expense("Lunch - Biriyani", "Food", 420, last_month_offset, "UPI")
        add_expense("Auto fare", "Transportation", 90, last_month_offset, "Cash")
        add_expense("Groceries", "Groceries", 2100, last_month_offset + 2, "Debit Card")
        add_expense("Electricity bill", "Utilities", 4200, last_month_offset + 3, "UPI")
        add_expense("Movie tickets", "Entertainment", 800, last_month_offset + 5, "Credit Card")
        add_expense("Medicines", "Healthcare", 560, last_month_offset + 7, "Cash")
        add_expense("Clothes shopping", "Shopping", 3200, last_month_offset + 8, "Credit Card")
        add_expense("Dining out", "Food", 1800, last_month_offset + 10, "UPI")
        add_expense("Bus fare", "Transportation", 240, last_month_offset + 12, "Cash")
        add_expense("Swiggy", "Food", 450, last_month_offset + 15, "UPI")
        add_expense("Books", "Education", 850, last_month_offset + 16, "Credit Card")
        add_expense("Mobile bill", "Utilities", 499, last_month_offset + 18, "UPI")

        # Income transactions
        add_expense(
            "Monthly Tech Salary", "Salary", 85000, 2, "Bank Transfer",
            notes="Direct deposit", tx_type="income",
        )
        add_expense(
            "Web Design Project", "Freelance", 25000, 10, "Bank Transfer",
            notes="Client milestone 2", tx_type="income",
        )

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
                category_id=get_cat(cat_name).id,
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
        add_recurring("Gym membership", "Healthcare", 2000, "Monthly", 20, "UPI")
        add_recurring("Internet bill", "Utilities", 999, "Monthly", 16, "UPI")
        add_recurring("Electricity bill", "Utilities", 4500, "Monthly", 27, "UPI")

        db.session.commit()
        print("     ✓ Recurring expenses created")

        # --- 7. Seed demo notifications ---
        print("  → Creating sample notifications...")
        if Notification.query.filter_by(user_id=user.id).count() == 0:
            n1 = Notification(
                user_id=user.id,
                title="Budget Utilization Alert",
                message="You have used 82% of your monthly entertainment budget.",
                type="warning",
                link="/budget",
                is_read=False,
            )
            n2 = Notification(
                user_id=user.id,
                title="Upcoming Subscription",
                message="Netflix Standard (₹649) is due in 14 days.",
                type="info",
                link="/recurring",
                is_read=False,
            )
            n3 = Notification(
                user_id=user.id,
                title="Savings Goal Milestone! 🎉",
                message="Congratulations! Your Emergency Fund reached 65% of its target.",
                type="success",
                link="/savings",
                is_read=True,
            )
            db.session.add_all([n1, n2, n3])
            db.session.commit()
            print("     ✓ Notifications created")

        print("\n✅ Seed complete!")
        print(f"   Demo login: {demo_email}")
        print("   Password:   demo1234")


if __name__ == "__main__":
    seed()
