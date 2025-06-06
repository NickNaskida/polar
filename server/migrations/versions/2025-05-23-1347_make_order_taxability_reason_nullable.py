"""Make Order taxability_reason nullable

Revision ID: 2289e219f18f
Revises: d50c07506383
Create Date: 2025-05-23 13:47:41.597025

"""

import sqlalchemy as sa
from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "2289e219f18f"
down_revision = "d50c07506383"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "orders", "taxability_reason", existing_type=sa.VARCHAR(), nullable=True
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "orders", "taxability_reason", existing_type=sa.VARCHAR(), nullable=False
    )
    # ### end Alembic commands ###
