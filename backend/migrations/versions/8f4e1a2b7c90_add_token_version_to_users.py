"""Add token_version to users

Revision ID: 8f4e1a2b7c90
Revises: 3c2b399d24d8
Create Date: 2026-09-26 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f4e1a2b7c90"
down_revision = "3c2b399d24d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajoute la version des jetons de session (0 par défaut)."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Supprime la version des jetons de session."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
