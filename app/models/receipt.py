"""
app/models/receipt.py — Receipt metadata model.

We NEVER store the actual file in the database.
We store only metadata (where the file lives in storage + original filename).

In development: files go to instance/uploads/ on the local filesystem.
In production: files go to an S3-compatible object store (Cloudflare R2, etc.).
The storage_key is the path/key in whichever storage backend is active.
"""

from datetime import datetime, timezone
from app import db


class Receipt(db.Model):
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)

    # Each receipt belongs to exactly one expense
    expense_id = db.Column(
        db.Integer,
        db.ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # One receipt per expense
        index=True,
    )

    # The path or key to find the file in storage
    storage_key = db.Column(db.String(500), nullable=False)

    # Original filename — kept for display only, NOT used for storage
    original_filename = db.Column(db.String(255), nullable=False)

    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # bytes

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Receipt expense_id={self.expense_id} key={self.storage_key}>"
