from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "2e10a8c1ee78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="是否管理员",
        ),
    )

    # 把已有用户的 is_admin 默认值设为 0（server_default 已覆盖，但这里显式保证一致性）
    op.execute("UPDATE users SET is_admin = 0 WHERE is_admin IS NULL")


def downgrade() -> None:
    op.drop_column("users", "is_admin")

