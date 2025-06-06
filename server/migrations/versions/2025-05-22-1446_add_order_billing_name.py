"""Add Order.billing_name

Revision ID: bba168067ce7
Revises: a0a402ba59be
Create Date: 2025-05-22 14:46:33.017044

"""

import sqlalchemy as sa
from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "bba168067ce7"
down_revision = "a0a402ba59be"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("orders", sa.Column("billing_name", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("orders", "billing_name")
    # ### end Alembic commands ###
