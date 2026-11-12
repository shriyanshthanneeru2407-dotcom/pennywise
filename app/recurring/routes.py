"""
app/recurring/routes.py — Recurring expense tracking.

This is for tracking purposes only — it does NOT automatically create
expense records. Users see upcoming recurring items and log them manually
when they occur.

Frequencies: Weekly, Monthly, Yearly
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models.recurring import RecurringExpense, FREQUENCIES
from app.models.expense import PAYMENT_METHODS
from app.models.category import Category

recurring_bp = Blueprint("recurring", __name__)


def _get_recurring_or_404(recurring_id: int) -> RecurringExpense:
    """Fetch recurring expense and verify ownership."""
    r = db.session.get(RecurringExpense, recurring_id)
    if not r or r.user_id != current_user.id:
        abort(404)
    return r


def _get_user_categories():
    return (
        Category.query
        .filter(or_(Category.user_id == None, Category.user_id == current_user.id))  # noqa: E711
        .order_by(Category.name)
        .all()
    )


def _advance_due_date(current_date: date, frequency: str) -> date:
    """Calculate the next due date based on frequency."""
    if frequency == "Weekly":
        return current_date + timedelta(weeks=1)
    elif frequency == "Yearly":
        return current_date + relativedelta(years=1)
    else:  # Monthly
        return current_date + relativedelta(months=1)


def _validate_recurring_form(form) -> tuple[dict, list]:
    errors = []
    data = {}

    description = form.get("description", "").strip()
    if not description:
        errors.append("Description is required.")
    else:
        data["description"] = description

    amount_str = form.get("amount", "").strip()
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            errors.append("Amount must be greater than zero.")
        else:
            data["amount"] = amount
    except (InvalidOperation, ValueError):
        errors.append("Amount must be a valid number.")

    try:
        cat_id = int(form.get("category_id", 0))
        category = db.session.get(Category, cat_id)
        if not category:
            errors.append("Please select a valid category.")
        else:
            data["category_id"] = cat_id
    except (ValueError, TypeError):
        errors.append("Please select a category.")

    frequency = form.get("frequency", "Monthly")
    if frequency not in FREQUENCIES:
        frequency = "Monthly"
    data["frequency"] = frequency

    next_due_str = form.get("next_due_date", "").strip()
    try:
        data["next_due_date"] = date.fromisoformat(next_due_str)
    except (ValueError, TypeError):
        errors.append("Please enter a valid next due date.")

    payment_method = form.get("payment_method", "Other")
    if payment_method not in PAYMENT_METHODS:
        payment_method = "Other"
    data["payment_method"] = payment_method

    return data, errors


@recurring_bp.route("/")
@recurring_bp.route("")
@login_required
def index():
    """List all recurring expenses, active ones first."""
    active = (
        RecurringExpense.query
        .filter_by(user_id=current_user.id, active=True)
        .order_by(RecurringExpense.next_due_date)
        .all()
    )
    inactive = (
        RecurringExpense.query
        .filter_by(user_id=current_user.id, active=False)
        .order_by(RecurringExpense.description)
        .all()
    )
    return render_template(
        "recurring/index.html",
        active=active,
        inactive=inactive,
        today=date.today(),
    )


@recurring_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    categories = _get_user_categories()

    if request.method == "POST":
        data, errors = _validate_recurring_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "recurring/form.html",
                categories=categories,
                frequencies=FREQUENCIES,
                payment_methods=PAYMENT_METHODS,
                form_data=request.form,
                action="Add",
            )

        recurring = RecurringExpense(
            user_id=current_user.id,
            currency=current_user.currency,
            **data,
        )
        db.session.add(recurring)
        db.session.commit()
        flash("Recurring expense added.", "success")
        return redirect(url_for("recurring.index"))

    return render_template(
        "recurring/form.html",
        categories=categories,
        frequencies=FREQUENCIES,
        payment_methods=PAYMENT_METHODS,
        form_data={"next_due_date": date.today().isoformat(), "frequency": "Monthly"},
        action="Add",
    )


@recurring_bp.route("/<int:recurring_id>/edit", methods=["GET", "POST"])
@login_required
def edit(recurring_id):
    recurring = _get_recurring_or_404(recurring_id)
    categories = _get_user_categories()

    if request.method == "POST":
        data, errors = _validate_recurring_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "recurring/form.html",
                categories=categories,
                frequencies=FREQUENCIES,
                payment_methods=PAYMENT_METHODS,
                form_data=request.form,
                recurring=recurring,
                action="Edit",
            )

        for key, value in data.items():
            setattr(recurring, key, value)

        db.session.commit()
        flash("Recurring expense updated.", "success")
        return redirect(url_for("recurring.index"))

    return render_template(
        "recurring/form.html",
        categories=categories,
        frequencies=FREQUENCIES,
        payment_methods=PAYMENT_METHODS,
        form_data={
            "description": recurring.description,
            "amount": recurring.amount,
            "category_id": recurring.category_id,
            "frequency": recurring.frequency,
            "next_due_date": recurring.next_due_date.isoformat(),
            "payment_method": recurring.payment_method,
        },
        recurring=recurring,
        action="Edit",
    )


@recurring_bp.route("/<int:recurring_id>/delete", methods=["POST"])
@login_required
def delete(recurring_id):
    recurring = _get_recurring_or_404(recurring_id)
    db.session.delete(recurring)
    db.session.commit()
    flash("Recurring expense deleted.", "success")
    return redirect(url_for("recurring.index"))


@recurring_bp.route("/<int:recurring_id>/toggle", methods=["POST"])
@login_required
def toggle(recurring_id):
    """Activate or pause a recurring expense."""
    recurring = _get_recurring_or_404(recurring_id)
    recurring.active = not recurring.active
    db.session.commit()
    status = "activated" if recurring.active else "paused"
    flash(f"Recurring expense {status}.", "success")
    return redirect(url_for("recurring.index"))


@recurring_bp.route("/<int:recurring_id>/log", methods=["POST"])
@login_required
def log_expense(recurring_id):
    """
    Quickly log a recurring item as an actual expense and advance next_due_date.
    This is a convenience action from the recurring list.
    """
    from app.models.expense import Expense

    recurring = _get_recurring_or_404(recurring_id)

    expense = Expense(
        user_id=current_user.id,
        category_id=recurring.category_id,
        amount=recurring.amount,
        currency=recurring.currency,
        description=recurring.description,
        expense_date=date.today(),
        payment_method=recurring.payment_method,
        notes=f"Logged from recurring: {recurring.frequency}",
    )
    db.session.add(expense)

    # Advance the due date
    recurring.next_due_date = _advance_due_date(recurring.next_due_date, recurring.frequency)
    db.session.commit()

    try:
        from app.notifications.routes import create_notification
        create_notification(
            user_id=current_user.id,
            title="Recurring Expense Logged",
            message=f"{recurring.description} ({current_user.currency_symbol}{recurring.amount:,.2f}) was recorded. Next due date: {recurring.next_due_date.strftime('%d %b %Y')}.",
            type_="info",
            link="/expenses",
        )
    except Exception:
        pass

    flash(f"Expense logged: {recurring.description}. Next due: {recurring.next_due_date.strftime('%d %b %Y')}.", "success")
    return redirect(url_for("recurring.index"))
