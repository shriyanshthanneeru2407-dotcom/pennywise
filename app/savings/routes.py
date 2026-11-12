"""
app/savings/routes.py — Savings goals and contribution tracking.
"""

from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.savings import SavingsGoal, SavingsContribution

savings_bp = Blueprint("savings", __name__)


@savings_bp.route("/")
@savings_bp.route("")
@login_required
def index():
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.created_at.desc()).all()
    active_goals = [g for g in goals if g.status == "active"]
    completed_goals = [g for g in goals if g.status == "completed" or g.is_completed]

    total_target = sum(g.target_amount for g in active_goals) if active_goals else Decimal("0.00")
    total_saved = sum(g.current_amount for g in active_goals) if active_goals else Decimal("0.00")
    total_remaining = max(Decimal("0.00"), total_target - total_saved)

    overall_pct = 0.0
    if total_target > 0:
        overall_pct = round((float(total_saved) / float(total_target)) * 100, 1)

    return render_template(
        "savings/index.html",
        active_goals=active_goals,
        completed_goals=completed_goals,
        total_target=total_target,
        total_saved=total_saved,
        total_remaining=total_remaining,
        overall_pct=overall_pct,
    )


@savings_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        target_str = request.form.get("target_amount", "0").strip()
        initial_str = request.form.get("initial_amount", "0").strip()
        category = request.form.get("category", "General").strip()
        target_date_str = request.form.get("target_date", "").strip()

        errors = []
        if not title:
            errors.append("Goal title is required.")

        try:
            target_amount = Decimal(target_str)
            if target_amount <= 0:
                errors.append("Target amount must be greater than zero.")
        except Exception:
            errors.append("Invalid target amount.")
            target_amount = Decimal("0.00")

        try:
            initial_amount = Decimal(initial_str) if initial_str else Decimal("0.00")
            if initial_amount < 0:
                errors.append("Initial amount cannot be negative.")
        except Exception:
            errors.append("Invalid initial amount.")
            initial_amount = Decimal("0.00")

        target_date = None
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                errors.append("Invalid target date.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("savings/form.html", action="Create", goal=None)

        goal = SavingsGoal(
            user_id=current_user.id,
            title=title,
            target_amount=target_amount,
            current_amount=initial_amount,
            target_date=target_date,
            category=category,
            status="completed" if initial_amount >= target_amount else "active",
        )
        db.session.add(goal)
        db.session.commit()

        if initial_amount > 0:
            contrib = SavingsContribution(
                goal_id=goal.id,
                amount=initial_amount,
                contribution_date=date.today(),
                notes="Initial deposit",
            )
            db.session.add(contrib)
            db.session.commit()

        flash(f"Savings goal '{title}' created successfully!", "success")
        return redirect(url_for("savings.index"))

    return render_template("savings/form.html", action="Create", goal=None)


@savings_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute(goal_id: int):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    amount_str = request.form.get("amount", "0").strip()
    notes = request.form.get("notes", "").strip() or None

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            flash("Contribution amount must be greater than zero.", "danger")
            return redirect(url_for("savings.index"))
    except Exception:
        flash("Invalid contribution amount.", "danger")
        return redirect(url_for("savings.index"))

    goal.current_amount += amount
    completed_now = False
    if goal.current_amount >= goal.target_amount:
        if goal.status != "completed":
            completed_now = True
        goal.status = "completed"

    contrib = SavingsContribution(
        goal_id=goal.id,
        amount=amount,
        contribution_date=date.today(),
        notes=notes,
    )
    db.session.add(contrib)
    db.session.commit()

    if completed_now:
        try:
            from app.notifications.routes import create_notification
            target_str = f"{current_user.currency_symbol}{goal.target_amount:,.2f}"
            create_notification(
                user_id=current_user.id,
                title="Savings Goal Completed! 🎉",
                message=f"Congratulations! You reached 100% of your '{goal.title}' target ({target_str})!",
                type_="success",
                link="/savings",
            )
        except Exception:
            pass

    flash(f"Deposited {current_user.currency_symbol}{amount:,.2f} toward '{goal.title}'!", "success")
    return redirect(url_for("savings.index"))


@savings_bp.route("/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete(goal_id: int):
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    title = goal.title
    db.session.delete(goal)
    db.session.commit()
    flash(f"Savings goal '{title}' was removed.", "info")
    return redirect(url_for("savings.index"))
