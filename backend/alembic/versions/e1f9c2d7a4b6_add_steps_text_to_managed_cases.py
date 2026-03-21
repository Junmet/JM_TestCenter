from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1f9c2d7a4b6"
down_revision = "d8a2b7c1e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("managed_cases", sa.Column("steps_text", sa.Text(), nullable=True, comment="用例步骤文本"))


def downgrade() -> None:
    op.drop_column("managed_cases", "steps_text")
