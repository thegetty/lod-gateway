"""Fix container constraint

Revision ID: :
Revises: bab6dc1e7e45
Create Date: 2026-03-27

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "ff9f39c62302"
down_revision = "bab6dc1e7e45"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("containers", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "container_identifier_unique", ["container_identifier"]
        )

    with op.batch_alter_table("containers", schema=None) as batch_op:
        batch_op.drop_constraint("container_identifier_unique", type_="unique")


def downgrade():
    pass
