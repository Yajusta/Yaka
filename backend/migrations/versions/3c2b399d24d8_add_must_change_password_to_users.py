"""Add must_change_password to users

Revision ID: 3c2b399d24d8
Revises: c1d2e3f4g5h6
Create Date: 2026-09-26 22:05:23.253373

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3c2b399d24d8"
down_revision = "c1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajoute le flag de changement de mot de passe obligatoire (faux par défaut)."""
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Supprime le flag de changement de mot de passe obligatoire."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("must_change_password")
