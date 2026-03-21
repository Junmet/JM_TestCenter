"""移除 UI 自动化相关表（与已删除的后端功能一致）。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h0a1b2c3d4e5"
down_revision = "g9h0i1j2k3l4"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return set(insp.get_table_names())


def upgrade() -> None:
    """
    MySQL：被外键引用的列上的索引不能先单独 DROP INDEX，需直接 DROP TABLE（先子表后父表）。
    """
    tables = _table_names()
    if "ui_automation_runs" in tables:
        op.drop_table("ui_automation_runs")
    tables = _table_names()
    if "ui_automation_cases" in tables:
        op.drop_table("ui_automation_cases")


def downgrade() -> None:
    # 表结构由 g9h0i1j2k3l4 定义；若需恢复请手动 downgrade 该 revision
    pass
