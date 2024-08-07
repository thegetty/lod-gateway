"""empty message

Revision ID: f059f3e51ea5
Revises: 7eb3a9f2a4be
Create Date: 2022-06-30 18:57:20.851157

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f059f3e51ea5"
down_revision = "7eb3a9f2a4be"
branch_labels = None
depends_on = None

#### This drops some unneeded indexes (to improve write performance), and adds a multicolumn sorted index to speed up
#### listing the versions associated with a record.


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_records_previous_version", table_name="records")
    op.drop_index("ix_versions_datetime_created", table_name="versions")
    op.create_index(
        "ix_versions_chronological_lookup",
        "versions",
        ["record_id", "datetime_updated", "entity_id"],
        unique=False,
        postgresql_using="btree",
        postgresql_ops={"datetime_updated": "DESC"},
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "ix_versions_chronological_lookup",
        table_name="versions",
        postgresql_using="btree",
        postgresql_ops={"datetime_updated": "DESC"},
    )
    op.create_index(
        "ix_versions_datetime_created", "versions", ["datetime_created"], unique=False
    )
    op.create_index(
        "ix_records_previous_version", "records", ["previous_version"], unique=False
    )
    # ### end Alembic commands ###
