"""add card_comments table

Revision ID: 756429e64d69
Revises: 54b30ffcd2aa
Create Date: 2025-09-08 18:34:26.314646

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "756429e64d69"
down_revision = "54b30ffcd2aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create card_comments table
    op.create_table(
        "card_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_card_comments_id"), "card_comments", ["id"], unique=False)


def downgrade() -> None:
    # Drop card_comments table
    op.drop_index(op.f("ix_card_comments_id"), table_name="card_comments")
    op.drop_table("card_comments")
