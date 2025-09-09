"""Add language preference to users

Revision ID: 689984d4c0de
Revises: 756429e64d69
Create Date: 2025-09-09 23:17:13.034234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '689984d4c0de'
down_revision = '756429e64d69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add language column to users table
    op.add_column('users', sa.Column('language', sa.String(length=2), nullable=True, server_default='fr'))
    
    # Update existing users to have French as default language
    op.execute("UPDATE users SET language = 'fr' WHERE language IS NULL")


def downgrade() -> None:
    # Remove language column from users table
    op.drop_column('users', 'language')