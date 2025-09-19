"""Rename French column names to English"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3b5d9a7f1a34"
down_revision = "689984d4c0de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column("titre", new_column_name="title")
        batch_op.alter_column("date_echeance", new_column_name="due_date")
        batch_op.alter_column("priorite", new_column_name="priority")

    with op.batch_alter_table("card_items") as batch_op:
        batch_op.alter_column("texte", new_column_name="text")

    with op.batch_alter_table("labels") as batch_op:
        batch_op.alter_column("nom", new_column_name="name")
        batch_op.alter_column("couleur", new_column_name="color")


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.alter_column("title", new_column_name="titre")
        batch_op.alter_column("due_date", new_column_name="date_echeance")
        batch_op.alter_column("priority", new_column_name="priorite")

    with op.batch_alter_table("card_items") as batch_op:
        batch_op.alter_column("text", new_column_name="texte")

    with op.batch_alter_table("labels") as batch_op:
        batch_op.alter_column("name", new_column_name="nom")
        batch_op.alter_column("color", new_column_name="couleur")
