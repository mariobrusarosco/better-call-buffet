"""index installment plans vendor id

Vendor usage counts look up installment plans by vendor_id; transactions and
subscriptions already have this index.

Revision ID: 5023d16fc221
Revises: b5274e931934
Create Date: 2026-10-08

"""

from typing import Sequence, Union

from alembic import op

revision: str = "5023d16fc221"
down_revision: Union[str, None] = "b5274e931934"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_installment_plans_vendor_id",
        "installment_plans",
        ["vendor_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_installment_plans_vendor_id", table_name="installment_plans")
