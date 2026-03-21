from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d8a2b7c1e9f0"
down_revision = "c3f4a8b9d012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户ID"),
        sa.Column("code", sa.String(length=64, collation="utf8mb4_unicode_ci"), nullable=False, comment="需求编号"),
        sa.Column("title", sa.String(length=255, collation="utf8mb4_unicode_ci"), nullable=False, comment="需求标题"),
        sa.Column("owner", sa.String(length=64, collation="utf8mb4_unicode_ci"), nullable=False, server_default="当前用户", comment="负责人"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active", comment="状态"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="p1", comment="优先级"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code"),
        comment="用例管理-需求表",
    )
    op.create_index("ix_managed_requirements_user_id", "managed_requirements", ["user_id"])

    op.create_table(
        "managed_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("requirement_id", sa.Integer(), nullable=False, comment="需求ID"),
        sa.Column("case_code", sa.String(length=64, collation="utf8mb4_unicode_ci"), nullable=False, comment="用例编号"),
        sa.Column("name", sa.String(length=255, collation="utf8mb4_unicode_ci"), nullable=False, comment="用例名称"),
        sa.Column("type_text", sa.String(length=32), nullable=False, server_default="功能", comment="类型"),
        sa.Column("priority_text", sa.String(length=16), nullable=False, server_default="P1", comment="优先级文本"),
        sa.Column("status_text", sa.String(length=32), nullable=False, server_default="启用", comment="状态文本"),
        sa.Column("last_run_at", sa.String(length=32), nullable=False, server_default="", comment="最后执行时间文本"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["requirement_id"], ["managed_requirements.id"], ondelete="CASCADE"),
        comment="用例管理-用例表",
    )
    op.create_index("ix_managed_cases_requirement_id", "managed_cases", ["requirement_id"])


def downgrade() -> None:
    op.drop_index("ix_managed_cases_requirement_id", table_name="managed_cases")
    op.drop_table("managed_cases")
    op.drop_index("ix_managed_requirements_user_id", table_name="managed_requirements")
    op.drop_table("managed_requirements")
