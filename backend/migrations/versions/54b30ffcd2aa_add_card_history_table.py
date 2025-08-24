"""add card history table

Revision ID: 54b30ffcd2aa
Revises: 
Create Date: 2025-08-24 14:13:32.528305

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54b30ffcd2aa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create card_history table
    op.create_table(
        'card_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['cards.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_card_history_id'), 'card_history', ['id'], unique=False)


def downgrade() -> None:
    # Drop card_history table
    op.drop_index(op.f('ix_card_history_id'), table_name='card_history')
    op.drop_table('card_history')