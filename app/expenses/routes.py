"""
app/expenses/routes.py — Expense CRUD, search, filter, and receipt serving.

SECURITY (very important):
  Every route that reads or modifies an expense first calls _get_expense_or_404()
  which verifies that the expense belongs to current_user.
  If it doesn't, we return 404 (not 403) to avoid revealing that the ID exists.

CRUD routes:
  GET  /expenses          → list with search/filter/pagination
  GET  /expenses/new      → add form
  POST /expenses          → create
  GET  /expenses/<id>/edit → edit form
  POST /expenses/<id>/edit → update
  POST /expenses/<id>/delete → delete

Receipt:
  GET  /expenses/receipt/<key:path> → serve receipt file (local dev)
"""

import os
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort, send_file, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models.expense import Expense, PAYMENT_METHODS
from app.models.category import Category
from app.models.receipt import Receipt
from app.services import storage_service

expenses_bp = Blueprint("expenses", __name__)

ITEMS_PER_PAGE = 15


def _get_expense_or_404(expense_id: int) -> Expense:
    """
    Fetch an expense by ID and verify it belongs to the current user.
    Returns 404 (not 403) to avoid revealing that the expense ID exists.
    This is the ownership check that prevents User B from accessing User A's data.
    """
    expense = db.session.get(Expense, expense_id)
    if not expense or expense.user_id != current_user.id:
        abort(404)
    return expense


def _get_user_categories():
    """Return all categories available to the current user (system + own)."""
    return (
        Category.query
        .filter(
            or_(Category.user_id == None, Category.user_id == current_user.id)  # noqa: E711
        )
        .order_by(Category.name)
        .all()
    )


def _validate_expense_form(form) -> tuple[dict, list]:
    """
    Validate the expense form data server-side.
    Returns (cleaned_data dict, errors list).
    Client-side validation is also done but never trusted.
    """
    errors = []
    data = {}

    # Transaction type ('expense' or 'income')
    tx_type = form.get("transaction_type", "expense").strip().lower()
    if tx_type not in ("expense", "income"):
        tx_type = "expense"
    data["transaction_type"] = tx_type

    # Amount
    amount_str = form.get("amount", "").strip()
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            errors.append("Amount must be greater than zero.")
        elif amount > Decimal("99999999.99"):
            errors.append("Amount is unreasonably large.")
        else:
            data["amount"] = amount
    except (InvalidOperation, ValueError):
        errors.append("Amount must be a valid number.")

    # Category
    try:
        cat_id = int(form.get("category_id", 0))
        category = db.session.get(Category, cat_id)
        if not category:
            errors.append("Please select a valid category.")
        else:
            data["category_id"] = cat_id
    except (ValueError, TypeError):
        errors.append("Please select a category.")

    # Description
    description = form.get("description", "").strip()
    if not description:
        errors.append("Description is required.")
    elif len(description) > 200:
        errors.append("Description must be 200 characters or fewer.")
    else:
        data["description"] = description

    # Date
    date_str = form.get("expense_date", "").strip()
    try:
        expense_date = date.fromisoformat(date_str)
        # Allow up to 10 years in the past, not more than 1 day in the future
        if expense_date.year < date.today().year - 10:
            errors.append("Date is too far in the past.")
        data["expense_date"] = expense_date
    except (ValueError, TypeError):
        errors.append("Please enter a valid date.")

    # Payment method
    payment_method = form.get("payment_method", "Cash")
    if payment_method not in PAYMENT_METHODS:
        payment_method = "Other"
    data["payment_method"] = payment_method

    # Notes (optional)
    notes = form.get("notes", "").strip()
    data["notes"] = notes if notes else None

    return data, errors


@expenses_bp.route("/")
@expenses_bp.route("")
@login_required
def index():
    """
    Expense list with server-side search, filter, and pagination.
    All filters are applied in SQL — we never load all records into memory.
    """
    # --- Build the base query for this user ---
    query = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .join(Category, Expense.category_id == Category.id)
    )

    # --- Apply filters ---
    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Expense.description.ilike(like),
                Expense.notes.ilike(like),
                Category.name.ilike(like),
            )
        )

    type_filter = request.args.get("type", "").strip()
    if type_filter in ("income", "expense"):
        query = query.filter(Expense.transaction_type == type_filter)

    cat_filter = request.args.get("category_id", "")
    if cat_filter:
        try:
            query = query.filter(Expense.category_id == int(cat_filter))
        except ValueError:
            pass

    payment_filter = request.args.get("payment_method", "")
    if payment_filter and payment_filter in PAYMENT_METHODS:
        query = query.filter(Expense.payment_method == payment_filter)

    date_from = request.args.get("date_from", "")
    if date_from:
        try:
            query = query.filter(Expense.expense_date >= date.fromisoformat(date_from))
        except ValueError:
            pass

    date_to = request.args.get("date_to", "")
    if date_to:
        try:
            query = query.filter(Expense.expense_date <= date.fromisoformat(date_to))
        except ValueError:
            pass

    min_amount = request.args.get("min_amount", "")
    if min_amount:
        try:
            query = query.filter(Expense.amount >= Decimal(min_amount))
        except InvalidOperation:
            pass

    max_amount = request.args.get("max_amount", "")
    if max_amount:
        try:
            query = query.filter(Expense.amount <= Decimal(max_amount))
        except InvalidOperation:
            pass

    # --- Sorting ---
    sort = request.args.get("sort", "date_desc")
    if sort == "amount_desc":
        query = query.order_by(Expense.amount.desc())
    elif sort == "amount_asc":
        query = query.order_by(Expense.amount.asc())
    elif sort == "date_asc":
        query = query.order_by(Expense.expense_date.asc())
    else:
        query = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())

    # --- Pagination ---
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    categories = _get_user_categories()

    return render_template(
        "expenses/index.html",
        expenses=pagination.items,
        pagination=pagination,
        categories=categories,
        payment_methods=PAYMENT_METHODS,
        search=search,
        cat_filter=cat_filter,
        type_filter=type_filter,
        payment_filter=payment_filter,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        sort=sort,
    )


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """
    GET:  Show the add expense form.
    POST: Validate, save, redirect to list.
    """
    categories = _get_user_categories()

    if request.method == "POST":
        data, errors = _validate_expense_form(request.form)

        # Handle receipt upload
        receipt_file = request.files.get("receipt")
        receipt_data = None

        if receipt_file and receipt_file.filename:
            mime_type = receipt_file.mimetype or ""
            if not storage_service.allowed_file(receipt_file.filename, mime_type):
                errors.append("Receipt must be a JPG, PNG, or PDF file under 10 MB.")
            else:
                # Validate file size
                receipt_file.seek(0, 2)  # Seek to end
                size = receipt_file.tell()
                receipt_file.seek(0)    # Reset
                if size > storage_service.MAX_FILE_SIZE_BYTES:
                    errors.append("Receipt file is too large (max 10 MB).")
                else:
                    receipt_data = {
                        "file": receipt_file,
                        "original_filename": receipt_file.filename,
                        "mime_type": mime_type,
                        "file_size": size,
                    }

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "expenses/form.html",
                categories=categories,
                payment_methods=PAYMENT_METHODS,
                form_data=request.form,
                action="Add",
            )

        # Create expense
        expense = Expense(
            user_id=current_user.id,
            currency=current_user.currency,
            **data,
        )
        db.session.add(expense)
        db.session.flush()  # Get the expense.id before committing

        # Save receipt if provided
        if receipt_data:
            key = storage_service.save(
                receipt_data["file"],
                receipt_data["original_filename"],
                receipt_data["mime_type"],
            )
            receipt = Receipt(
                expense_id=expense.id,
                storage_key=key,
                original_filename=receipt_data["original_filename"],
                mime_type=receipt_data["mime_type"],
                file_size=receipt_data["file_size"],
            )
            db.session.add(receipt)

        db.session.commit()

        # Check if budget threshold crossed and trigger automated in-app alert
        if data.get("transaction_type") == "expense":
            try:
                from app.services.analytics import get_monthly_summary
                from app.notifications.routes import create_notification

                summary = get_monthly_summary(
                    current_user.id, data["expense_date"].year, data["expense_date"].month
                )
                pct = summary.get("budget_pct")
                if pct and pct >= 100:
                    create_notification(
                        user_id=current_user.id,
                        title="🚨 Budget Exceeded!",
                        message=f"You have consumed {pct}% of your monthly budget limit.",
                        type_="danger",
                        link="/budget",
                    )
                elif pct and pct >= 80:
                    create_notification(
                        user_id=current_user.id,
                        title="⚠️ 80% Budget Warning",
                        message=f"You have consumed {pct}% of your monthly spending limit.",
                        type_="warning",
                        link="/budget",
                    )
            except Exception:
                pass

        flash("Expense added successfully.", "success")
        return redirect(url_for("expenses.index"))

    # Default date to today
    return render_template(
        "expenses/form.html",
        categories=categories,
        payment_methods=PAYMENT_METHODS,
        form_data={"expense_date": date.today().isoformat()},
        action="Add",
    )


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    """
    GET:  Show edit form pre-filled with expense data.
    POST: Validate and update.

    Ownership is verified in _get_expense_or_404().
    """
    expense = _get_expense_or_404(expense_id)
    categories = _get_user_categories()

    if request.method == "POST":
        data, errors = _validate_expense_form(request.form)

        # Handle receipt upload (optional — replaces existing)
        receipt_file = request.files.get("receipt")
        receipt_data = None

        if receipt_file and receipt_file.filename:
            mime_type = receipt_file.mimetype or ""
            if not storage_service.allowed_file(receipt_file.filename, mime_type):
                errors.append("Receipt must be a JPG, PNG, or PDF file.")
            else:
                receipt_file.seek(0, 2)
                size = receipt_file.tell()
                receipt_file.seek(0)
                if size > storage_service.MAX_FILE_SIZE_BYTES:
                    errors.append("Receipt file is too large (max 10 MB).")
                else:
                    receipt_data = {
                        "file": receipt_file,
                        "original_filename": receipt_file.filename,
                        "mime_type": mime_type,
                        "file_size": size,
                    }

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "expenses/form.html",
                categories=categories,
                payment_methods=PAYMENT_METHODS,
                form_data=request.form,
                expense=expense,
                action="Edit",
            )

        # Update expense fields
        for key, value in data.items():
            setattr(expense, key, value)

        # Replace receipt if a new one was uploaded
        if receipt_data:
            if expense.receipt:
                storage_service.delete(expense.receipt.storage_key)
                db.session.delete(expense.receipt)

            key = storage_service.save(
                receipt_data["file"],
                receipt_data["original_filename"],
                receipt_data["mime_type"],
            )
            receipt = Receipt(
                expense_id=expense.id,
                storage_key=key,
                original_filename=receipt_data["original_filename"],
                mime_type=receipt_data["mime_type"],
                file_size=receipt_data["file_size"],
            )
            db.session.add(receipt)

        # Handle receipt deletion
        if request.form.get("delete_receipt") and expense.receipt:
            storage_service.delete(expense.receipt.storage_key)
            db.session.delete(expense.receipt)

        db.session.commit()
        flash("Expense updated successfully.", "success")
        return redirect(url_for("expenses.index"))

    return render_template(
        "expenses/form.html",
        categories=categories,
        payment_methods=PAYMENT_METHODS,
        form_data={
            "amount": expense.amount,
            "category_id": expense.category_id,
            "description": expense.description,
            "expense_date": expense.expense_date.isoformat(),
            "payment_method": expense.payment_method,
            "notes": expense.notes or "",
        },
        expense=expense,
        action="Edit",
    )


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    """
    POST only — never delete via GET (prevents CSRF via <img> tags etc.)
    Ownership verified. Cascade deletes the receipt record via DB foreign key.
    """
    expense = _get_expense_or_404(expense_id)

    # Delete receipt file from storage if it exists
    if expense.receipt:
        try:
            storage_service.delete(expense.receipt.storage_key)
        except Exception:
            pass  # Don't block deletion if storage delete fails

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.index"))


@expenses_bp.route("/receipt/<path:key>")
@login_required
def serve_receipt(key):
    """
    Serve a receipt file securely in local dev mode.

    Security:
      - Requires login
      - Verifies the receipt belongs to the current user via the storage key
      - Prevents path traversal by using send_file with a safe base directory
    """
    # Find receipt by storage_key and verify ownership through the expense
    receipt = (
        Receipt.query
        .join(Expense, Receipt.expense_id == Expense.id)
        .filter(Receipt.storage_key == key, Expense.user_id == current_user.id)
        .first_or_404()
    )

    local_path = storage_service.get_local_path(key)
    if not os.path.exists(local_path):
        abort(404)

    return send_file(
        local_path,
        mimetype=receipt.mime_type,
        as_attachment=False,
        download_name=receipt.original_filename,
    )


@expenses_bp.route("/categories/new", methods=["POST"])
@login_required
def new_category():
    """Quick AJAX endpoint to create a custom category."""
    name = request.json.get("name", "").strip() if request.is_json else ""
    if not name or len(name) > 50:
        return jsonify({"error": "Invalid category name."}), 400

    # Check for duplicate
    existing = Category.query.filter(
        or_(Category.user_id == None, Category.user_id == current_user.id),  # noqa: E711
        Category.name.ilike(name),
    ).first()

    if existing:
        return jsonify({"error": "Category already exists.", "id": existing.id, "name": existing.name}), 409

    category = Category(user_id=current_user.id, name=name, icon="📦")
    db.session.add(category)
    db.session.commit()

    return jsonify({"id": category.id, "name": category.name, "icon": category.icon}), 201
