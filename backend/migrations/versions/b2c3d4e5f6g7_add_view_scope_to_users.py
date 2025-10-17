"""Add view_scope column to users table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if view_scope column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'view_scope' not in columns:
        # Add view_scope column to users table with enum values
        # Using a string column with check constraint for enum values
        op.add_column('users', sa.Column('view_scope', sa.String(length=25), nullable=False, server_default='all'))
        
        # Add check constraint to ensure valid enum values
        op.execute("ALTER TABLE users ADD CONSTRAINT chk_view_scope CHECK (view_scope IN ('all', 'unassigned_plus_mine', 'mine_only'))")
    else:
        # Column exists, ensure all existing users have view_scope set to 'all'
        # This handles the case where column was added manually but default wasn't applied
        op.execute("UPDATE users SET view_scope = 'all' WHERE view_scope IS NULL OR view_scope = ''")
        
        # Just ensure the constraint is present
        try:
            op.execute("ALTER TABLE users ADD CONSTRAINT chk_view_scope CHECK (view_scope IN ('all', 'unassigned_plus_mine', 'mine_only'))")
        except Exception:
            # Constraint might already exist, ignore error
            pass


def downgrade() -> None:
    # Remove check constraint first
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_view_scope")
    
    # Remove view_scope column from users table
    op.drop_column('users', 'view_scope')
