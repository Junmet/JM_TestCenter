from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e1f9c2d7a4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "managed_cases",
        sa.Column(
            "execution_status",
            sa.String(length=32),
            nullable=False,
            server_default="not_executed",
            comment="执行状态：not_executed/success/failed/blocked",
        ),
    )


def downgrade() -> None:
    op.drop_column("managed_cases", "execution_status")
