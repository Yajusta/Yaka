"""Add dictionary tables

Revision ID: c1d2e3f4g5h6
Revises: b2c3d4e5f6g7
Create Date: 2025-10-17 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add global_dictionary and personal_dictionary tables.

    This migration creates two tables:
    - global_dictionary: for admin-managed vocabulary accessible to all users
    - personal_dictionary: for user-specific vocabulary with unique constraint on (user_id, term)
    """
    # Create global_dictionary table
    op.create_table(
        "global_dictionary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=32), nullable=False),
        sa.Column("definition", sa.String(length=250), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("global_dictionary", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_global_dictionary_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_global_dictionary_term"), ["term"], unique=True)

    # Create personal_dictionary table
    op.create_table(
        "personal_dictionary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=32), nullable=False),
        sa.Column("definition", sa.String(length=250), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "term", name="uq_user_term"),
    )
    with op.batch_alter_table("personal_dictionary", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_personal_dictionary_id"), ["id"], unique=False)


def downgrade() -> None:
    """Remove global_dictionary and personal_dictionary tables.

    This migration removes both dictionary tables.
    """
    # Drop personal_dictionary table
    with op.batch_alter_table("personal_dictionary", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_personal_dictionary_id"))
    op.drop_table("personal_dictionary")

    # Drop global_dictionary table
    with op.batch_alter_table("global_dictionary", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_global_dictionary_term"))
        batch_op.drop_index(batch_op.f("ix_global_dictionary_id"))
    op.drop_table("global_dictionary")

