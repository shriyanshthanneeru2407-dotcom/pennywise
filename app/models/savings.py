"""
app/models/savings.py — Savings Goals and Contributions models.
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from app import db


class SavingsGoal(db.Model):
    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    current_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), nullable=False, default="General")
    status = db.Column(db.String(20), nullable=False, default="active")  # 'active', 'completed', 'paused'

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    contributions = db.relationship("SavingsContribution", backref="goal", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def progress_pct(self) -> float:
        """Percentage of target reached (capped at 100 for gauge display)."""
        if not self.target_amount or self.target_amount <= 0:
            return 0.0
        pct = (float(self.current_amount) / float(self.target_amount)) * 100
        return round(pct, 1)

    @property
    def remaining_amount(self) -> Decimal:
        """Remaining amount to reach goal."""
        rem = self.target_amount - self.current_amount
        return max(Decimal("0.00"), rem)

    @property
    def is_completed(self) -> bool:
        return self.current_amount >= self.target_amount

    def __repr__(self) -> str:
        return f"<SavingsGoal {self.title} {self.current_amount}/{self.target_amount}>"


class SavingsContribution(db.Model):
    __tablename__ = "savings_contributions"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    contribution_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<SavingsContribution {self.amount} for goal {self.goal_id}>"
