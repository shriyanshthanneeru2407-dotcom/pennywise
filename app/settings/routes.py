"""
app/settings/routes.py — User profile, preferences, and account management.

Routes:
  GET  /settings         → Profile/settings page
  POST /settings/profile → Update name, email, date format
  POST /settings/password → Change password
  POST /settings/preferences → Update currency, theme
  GET  /export/expenses.csv → Download CSV export
  POST /settings/delete-account → Delete account (with confirmation)
"""

import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user, logout_user
from sqlalchemy import or_
from app import db
from app.models.user import User
from app.models.category import Category
from app.models.expense import Expense
from app.services.export_service import generate_expenses_csv

settings_bp = Blueprint("settings", __name__)

SUPPORTED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "AED", "SGD", "CHF"]
SUPPORTED_THEMES = ["light", "dark"]
DATE_FORMATS = ["%d %b %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


def _is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


@settings_bp.route("/")
@settings_bp.route("")
@login_required
def index():
    user_categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    system_categories = Category.query.filter_by(user_id=None).order_by(Category.name).all()
    return render_template(
        "settings/index.html",
        currencies=SUPPORTED_CURRENCIES,
        themes=SUPPORTED_THEMES,
        date_formats=DATE_FORMATS,
        user_categories=user_categories,
        system_categories=system_categories,
    )


@settings_bp.route("/category/new", methods=["POST"])
@login_required
def add_category():
    """Create a new custom category for the current user."""
    name = request.form.get("name", "").strip()
    category_type = request.form.get("category_type", "expense").strip().lower()
    icon = request.form.get("icon", "🏷️").strip() or "🏷️"
    color = request.form.get("color", "#00e676").strip() or "#00e676"

    if category_type not in ("expense", "income"):
        category_type = "expense"

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("settings.index"))

    if len(name) > 50:
        flash("Category name must be under 50 characters.", "danger")
        return redirect(url_for("settings.index"))

    # Check duplicate name for this user
    existing = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id.is_(None)),
        Category.name.ilike(name),
        Category.category_type == category_type,
    ).first()

    if existing:
        flash(f"A {category_type} category named '{name}' already exists.", "warning")
        return redirect(url_for("settings.index"))

    new_cat = Category(
        user_id=current_user.id,
        name=name,
        category_type=category_type,
        icon=icon,
        color=color,
    )
    db.session.add(new_cat)
    db.session.commit()

    flash(f"Custom category '{new_cat.icon} {new_cat.name}' created successfully.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/category/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id):
    """Delete a custom category owned by the current user."""
    category = db.session.get(Category, category_id)

    if not category or category.user_id != current_user.id:
        flash("You can only delete your own custom categories.", "danger")
        return redirect(url_for("settings.index"))

    # Reassign existing expenses to the default 'Other' category if available
    other_cat = Category.query.filter_by(user_id=None, name="Other").first()
    if other_cat:
        Expense.query.filter_by(category_id=category.id, user_id=current_user.id).update(
            {"category_id": other_cat.id}
        )

    cat_name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f"Category '{cat_name}' has been deleted.", "info")
    return redirect(url_for("settings.index"))


@settings_bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    date_format = request.form.get("date_format", "%d %b %Y")

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or not _is_valid_email(email):
        errors.append("A valid email address is required.")
    if date_format not in DATE_FORMATS:
        date_format = "%d %b %Y"

    # Check email uniqueness (excluding self)
    if email and email != current_user.email:
        existing = User.query.filter_by(email=email).first()
        if existing:
            errors.append("That email address is already in use.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return redirect(url_for("settings.index"))

    current_user.name = name
    current_user.email = email
    current_user.date_format = date_format
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/password", methods=["POST"])
@login_required
def update_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("settings.index"))

    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "danger")
        return redirect(url_for("settings.index"))

    if new_password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("settings.index"))

    current_user.set_password(new_password)
    db.session.commit()
    flash("Password updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/preferences", methods=["POST"])
@login_required
def update_preferences():
    currency = request.form.get("currency", "INR")
    theme = request.form.get("theme", "light")

    if currency not in SUPPORTED_CURRENCIES:
        currency = "INR"
    if theme not in SUPPORTED_THEMES:
        theme = "light"

    current_user.currency = currency
    current_user.theme = theme
    db.session.commit()
    flash("Preferences updated.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/export/expenses.csv")
@login_required
def export_expenses():
    """Generate and download a CSV of the user's expenses."""
    csv_content = generate_expenses_csv(current_user.id)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=pennywise-transactions.csv"
        },
    )


@settings_bp.route("/backup/json")
@login_required
def backup_json():
    """
    Export all user financial records as an RFC 8259 JSON package
    for data portability and offsite backup.
    """
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.expense_date.desc()).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    payload = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "currency": current_user.currency,
            "theme": current_user.theme,
        },
        "custom_categories": [
            {"name": c.name, "category_type": c.category_type, "icon": c.icon, "color": c.color}
            for c in categories
        ],
        "transactions": [
            {
                "date": e.expense_date.isoformat(),
                "description": e.description,
                "amount": str(e.amount),
                "transaction_type": e.transaction_type,
                "payment_method": e.payment_method,
                "category": e.category.name if e.category else None,
                "notes": e.notes,
            }
            for e in expenses
        ],
    }
    return Response(
        json.dumps(payload, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=pennywise-backup-{date.today().isoformat()}.json"
        },
    )


@settings_bp.route("/backup/import", methods=["POST"])
@login_required
def import_backup_json():
    """
    Restore or import user financial records from an uploaded JSON backup.
    Validates schema, recreates custom categories, and inserts transactions.
    """
    file = request.files.get("backup_file")
    if not file or not file.filename:
        flash("Please select a valid PennyWise JSON backup file.", "warning")
        return redirect(url_for("settings.index"))

    try:
        data = json.load(file)
    except Exception:
        flash("Invalid JSON format. Please upload a valid JSON file.", "danger")
        return redirect(url_for("settings.index"))

    if not isinstance(data, dict) or "transactions" not in data:
        flash("Unrecognized backup structure. Missing 'transactions' array.", "danger")
        return redirect(url_for("settings.index"))

    # Map existing categories
    cat_map = {}
    cats = Category.query.filter(or_(Category.user_id == None, Category.user_id == current_user.id)).all()  # noqa: E711
    for c in cats:
        cat_map[c.name.lower()] = c

    # Create missing custom categories
    imported_cats = 0
    for cat_data in data.get("custom_categories", []):
        cat_name = cat_data.get("name", "").strip()
        if cat_name and cat_name.lower() not in cat_map:
            new_cat = Category(
                name=cat_name,
                category_type=cat_data.get("category_type", "expense"),
                icon=cat_data.get("icon", "🏷️"),
                color=cat_data.get("color", "#00e676"),
                user_id=current_user.id,
            )
            db.session.add(new_cat)
            db.session.flush()
            cat_map[cat_name.lower()] = new_cat
            imported_cats += 1

    # Default category fallback
    default_expense_cat = Category.query.filter_by(name="Other Expense").first()
    default_income_cat = Category.query.filter_by(name="Other Income").first()

    imported_count = 0
    for item in data.get("transactions", []):
        try:
            amt = Decimal(str(item.get("amount", "0"))).quantize(Decimal("0.01"))
            if amt <= 0:
                continue
            exp_date = date.fromisoformat(item["date"])
            t_type = item.get("transaction_type", "expense")
            cat_name = (item.get("category") or "").strip().lower()
            category = cat_map.get(cat_name)
            if not category:
                category = default_income_cat if t_type == "income" else default_expense_cat

            expense = Expense(
                user_id=current_user.id,
                category_id=category.id if category else None,
                amount=amt,
                currency=current_user.currency,
                transaction_type=t_type,
                description=item.get("description", "Imported Transaction")[:128],
                expense_date=exp_date,
                payment_method=item.get("payment_method", "Other"),
                notes=item.get("notes"),
            )
            db.session.add(expense)
            imported_count += 1
        except Exception:
            continue

    db.session.commit()
    flash(
        f"Successfully imported {imported_count} transaction{'s' if imported_count != 1 else ''} "
        f"and {imported_cats} custom categor{'ies' if imported_cats != 1 else 'y'} from backup!",
        "success",
    )
    return redirect(url_for("expenses.index"))


@settings_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    """
    Permanently delete the user account.
    Requires typing 'DELETE' as confirmation to prevent accidental deletion.
    Cascade foreign keys ensure all expenses/budgets/etc. are removed.
    This is a POST-only route (never GET) for CSRF protection.
    """
    confirm = request.form.get("confirm_text", "").strip()

    if confirm != "DELETE":
        flash("Please type DELETE to confirm account deletion.", "danger")
        return redirect(url_for("settings.index"))

    user = current_user._get_current_object()
    logout_user()

    db.session.delete(user)
    db.session.commit()

    flash("Your account has been permanently deleted.", "info")
    return redirect(url_for("main.index"))
