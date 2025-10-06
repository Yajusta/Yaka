"""Add description to labels and lists

Revision ID: a1b2c3d4e5f6
Revises: 9a8b7c6d5e4f
Create Date: 2025-10-06 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9a8b7c6d5e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add description column to labels and kanban_lists tables.

    This migration adds an optional description field (VARCHAR(255))
    to both the labels and kanban_lists tables.
    """
    # Add description column to labels table
    with op.batch_alter_table("labels", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.String(length=255), nullable=True))

    # Add description column to kanban_lists table
    with op.batch_alter_table("kanban_lists", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove description column from labels and kanban_lists tables.

    This migration removes the description field from both tables.
    """
    # Remove description column from kanban_lists table
    with op.batch_alter_table("kanban_lists", schema=None) as batch_op:
        batch_op.drop_column("description")

    # Remove description column from labels table
    with op.batch_alter_table("labels", schema=None) as batch_op:
        batch_op.drop_column("description")
