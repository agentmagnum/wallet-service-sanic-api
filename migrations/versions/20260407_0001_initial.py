from __future__ import annotations

from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import table

from app.security import hash_password

# revision identifiers, used by Alembic.
revision = "20260407_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role_enum = sa.Enum("user", "admin", name="userrole", native_enum=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("transaction_id", name="uq_payments_transaction_id"),
    )
    op.create_index("ix_payments_transaction_id", "payments", ["transaction_id"], unique=False)
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)
    op.create_index("ix_payments_account_id", "payments", ["account_id"], unique=False)

    users_table = table(
        "users",
        sa.Column("id", sa.Integer()),
        sa.Column("email", sa.String(length=255)),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("password_hash", sa.String(length=255)),
        sa.Column("role", sa.String(length=16)),
    )

    accounts_table = table(
        "accounts",
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("balance", sa.Numeric(12, 2)),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "id": 1,
                "email": "user@example.com",
                "full_name": "Test User",
                "password_hash": hash_password("UserPass123!"),
                "role": "user",
            },
            {
                "id": 2,
                "email": "admin@example.com",
                "full_name": "Test Admin",
                "password_hash": hash_password("AdminPass123!"),
                "role": "admin",
            },
        ],
    )

    op.bulk_insert(
        accounts_table,
        [
            {
                "id": 1,
                "user_id": 1,
                "balance": Decimal("0.00"),
            }
        ],
    )

    op.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users));")
    op.execute("SELECT setval(pg_get_serial_sequence('accounts', 'id'), (SELECT MAX(id) FROM accounts));")
    op.execute("SELECT setval(pg_get_serial_sequence('payments', 'id'), COALESCE((SELECT MAX(id) FROM payments), 1));")


def downgrade() -> None:
    op.drop_index("ix_payments_account_id", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_index("ix_payments_transaction_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

