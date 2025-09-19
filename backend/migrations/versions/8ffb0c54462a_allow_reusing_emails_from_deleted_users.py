"""Allow reusing emails from logically deleted users"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8ffb0c54462a"
down_revision = "3b5d9a7f1a34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Relax email uniqueness to ignore logically deleted rows."""
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=False,
            unique=False,
        )

    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    condition = sa.text("status != 'DELETED'")
    op.create_index(
        "ux_users_email_not_deleted",
        "users",
        ["email"],
        unique=True,
        sqlite_where=condition,
        postgresql_where=condition,
    )


def downgrade() -> None:
    """Restore strict email uniqueness across all rows."""
    op.drop_index("ux_users_email_not_deleted", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(),
            nullable=False,
            unique=True,
        )
