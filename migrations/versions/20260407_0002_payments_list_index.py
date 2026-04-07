from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260407_0002"
down_revision = "20260407_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_payments_user_created_id",
        "payments",
        ["user_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payments_user_created_id", table_name="payments")
