"""Add entity type index

Revision ID: 3f57f4a875c6
Revises: 95195abeb123
Create Date: 2021-05-25 16:50:03.455788

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f57f4a875c6"
down_revision = "95195abeb123"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        op.f("ix_records_entity_type"), "records", ["entity_type"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_records_entity_type"), table_name="records")
    # ### end Alembic commands ###
