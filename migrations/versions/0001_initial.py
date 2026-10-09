"""initial schema: users, expenses, audit_logs

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The app also calls Base.metadata.create_all() on startup, so a database
    # may already have these tables; only create what is missing.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=False),
            sa.Column("role", sa.Enum("employee", "manager", "admin", name="roleenum"), nullable=False),
            sa.Column("is_active", sa.Boolean()),
            sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("ix_users_manager_id", "users", ["manager_id"])

    if "expenses" not in existing:
        op.create_table(
            "expenses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column(
                "status",
                sa.Enum("draft", "submitted", "approved", "rejected", "reimbursed", name="expensestatus"),
                nullable=False,
            ),
            sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("reviewer_comment", sa.Text()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_expenses_id", "expenses", ["id"])
        op.create_index("ix_expenses_owner_id", "expenses", ["owner_id"])

    if "audit_logs" not in existing:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id"), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("from_status", sa.String()),
            sa.Column("to_status", sa.String()),
            sa.Column("comment", sa.Text()),
            sa.Column("timestamp", sa.DateTime()),
        )
        op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
        op.create_index("ix_audit_logs_expense_id", "audit_logs", ["expense_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("expenses")
    op.drop_table("users")
    sa.Enum(name="expensestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="roleenum").drop(op.get_bind(), checkfirst=True)
