"""Update user roles to new structure

Revision ID: 9a8b7c6d5e4f
Revises: 8ffb0c54462a
Create Date: 2025-09-30 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a8b7c6d5e4f"
down_revision = "8ffb0c54462a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migrate old roles to new role structure (case-insensitive).

    Step 1: Drop the old unique constraint on email (status != 'DELETED')
    Step 2: Increase role column length from VARCHAR(5) to VARCHAR(20)
    Step 3: Update role values to new structure (lowercase)
    Step 4: Update status values to lowercase for consistency
    Step 5: Recreate unique constraint with lowercase 'deleted'

    Role mapping:
    - admin -> admin (unchanged)
    - user -> editor (standard user becomes editor)
    - read_only -> visitor (read-only becomes visitor)
    - comments_only -> commenter (comments-only becomes commenter)
    - assigned_only -> contributor (assigned-only becomes contributor)

    Status mapping:
    - ACTIVE -> active
    - INVITED -> invited
    - DELETED -> deleted
    """
    # Step 1: Drop the old unique constraint (it checks status != 'DELETED' in uppercase)
    # Use IF EXISTS to handle cases where the index might not exist yet
    op.execute("DROP INDEX IF EXISTS ux_users_email_not_deleted")

    # Step 2: Increase role column length to accommodate longer role names
    # Old: VARCHAR(5) - sufficient for 'admin', 'user'
    # New: VARCHAR(20) - needed for 'contributor' (11 chars), 'supervisor' (10 chars)
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.VARCHAR(length=5),
            type_=sa.VARCHAR(length=20),
            existing_nullable=False,
        )

    # Step 3: Update roles with case-insensitive matching
    # Using LOWER() to handle any case variations (e.g., "ADmiN" -> "admin")
    op.execute(
        """
        UPDATE users SET role = CASE
            WHEN LOWER(role) = 'admin' THEN 'admin'
            WHEN LOWER(role) = 'user' THEN 'editor'
            WHEN LOWER(role) = 'read_only' THEN 'visitor'
            WHEN LOWER(role) = 'comments_only' THEN 'commenter'
            WHEN LOWER(role) = 'assigned_only' THEN 'contributor'
            ELSE 'visitor'
        END
    """
    )

    # Step 4: Convert status values to lowercase for consistency
    op.execute(
        """
        UPDATE users SET status = LOWER(status)
    """
    )

    # Step 5: Recreate the unique constraint with lowercase 'deleted'
    condition = sa.text("status != 'deleted'")
    op.create_index(
        "ux_users_email_not_deleted",
        "users",
        ["email"],
        unique=True,
        sqlite_where=condition,
        postgresql_where=condition,
    )


def downgrade() -> None:
    """Revert to old role structure (case-insensitive).

    Step 1: Drop the new unique constraint (status != 'deleted')
    Step 2: Revert status values to uppercase
    Step 3: Recreate unique constraint with uppercase 'DELETED'
    Step 4: Revert role values to old structure
    Step 5: Decrease role column length from VARCHAR(20) to VARCHAR(5)

    Reverse mapping:
    - admin -> admin (unchanged)
    - supervisor -> admin (downgrade to admin)
    - editor -> user
    - contributor -> assigned_only
    - commenter -> comments_only
    - visitor -> read_only

    Status reverse mapping:
    - active -> ACTIVE
    - invited -> INVITED
    - deleted -> DELETED
    """
    # Step 1: Drop the new unique constraint (it checks status != 'deleted' in lowercase)
    # Use IF EXISTS to handle cases where the index might not exist
    op.execute("DROP INDEX IF EXISTS ux_users_email_not_deleted")

    # Step 2: Revert status values to uppercase
    op.execute(
        """
        UPDATE users SET status = UPPER(status)
    """
    )

    # Step 3: Recreate the unique constraint with uppercase 'DELETED'
    condition = sa.text("status != 'DELETED'")
    op.create_index(
        "ux_users_email_not_deleted",
        "users",
        ["email"],
        unique=True,
        sqlite_where=condition,
        postgresql_where=condition,
    )

    # Step 4: Revert role values
    op.execute(
        """
        UPDATE users SET role = CASE
            WHEN LOWER(role) = 'admin' THEN 'admin'
            WHEN LOWER(role) = 'supervisor' THEN 'admin'
            WHEN LOWER(role) = 'editor' THEN 'user'
            WHEN LOWER(role) = 'contributor' THEN 'assigned_only'
            WHEN LOWER(role) = 'commenter' THEN 'comments_only'
            WHEN LOWER(role) = 'visitor' THEN 'read_only'
            ELSE 'read_only'
        END
    """
    )

    # Step 5: Revert role column length to original size
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.VARCHAR(length=20),
            type_=sa.VARCHAR(length=5),
            existing_nullable=False,
        )
