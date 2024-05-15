"""empty message

Revision ID: 51333de9b9b1
Revises: 411e0b2175f8
Create Date: 2020-09-17 21:57:04.487245

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from flaskapp.models.record import Record


# revision identifiers, used by Alembic.
revision = "51333de9b9b1"
down_revision = "411e0b2175f8"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("records", sa.Column("checksum", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("records", "checksum")
    # ### end Alembic commands ###
