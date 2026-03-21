from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3f4a8b9d012"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="上传用户ID"),
        sa.Column(
            "source_name",
            sa.String(length=255, collation="utf8mb4_unicode_ci"),
            nullable=False,
            comment="原始文件名",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="generated",
            comment="状态: generated/failed",
        ),
        sa.Column("context_summary", sa.Text(), nullable=False, comment="文档摘要"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="用例生成-需求文档记录",
    )
    op.create_index("ix_case_requirements_user_id", "case_requirements", ["user_id"])

    op.create_table(
        "generated_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="主键"),
        sa.Column("requirement_id", sa.Integer(), nullable=False, comment="需求记录ID"),
        sa.Column(
            "case_code",
            sa.String(length=64, collation="utf8mb4_unicode_ci"),
            nullable=False,
            comment="用例编号",
        ),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="P2", comment="优先级"),
        sa.Column(
            "module",
            sa.String(length=128, collation="utf8mb4_unicode_ci"),
            nullable=False,
            server_default="",
            comment="模块",
        ),
        sa.Column(
            "title",
            sa.String(length=255, collation="utf8mb4_unicode_ci"),
            nullable=False,
            comment="测试标题",
        ),
        sa.Column("summary", sa.Text(), nullable=False, comment="摘要"),
        sa.Column("preconditions", sa.Text(), nullable=False, comment="前置条件"),
        sa.Column("steps", sa.JSON(), nullable=False, comment="测试步骤"),
        sa.Column("expected", sa.JSON(), nullable=False, comment="期望结果"),
        sa.Column("actual_result", sa.Text(), nullable=False, comment="实际结果"),
        sa.Column("test_type", sa.String(length=64), nullable=False, server_default="", comment="测试类型"),
        sa.Column("data", sa.Text(), nullable=False, comment="测试数据"),
        sa.Column("remarks", sa.Text(), nullable=False, comment="备注"),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="0", comment="是否确认"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.ForeignKeyConstraint(["requirement_id"], ["case_requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="用例生成-测试用例记录",
    )
    op.create_index("ix_generated_cases_requirement_id", "generated_cases", ["requirement_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_cases_requirement_id", table_name="generated_cases")
    op.drop_table("generated_cases")
    op.drop_index("ix_case_requirements_user_id", table_name="case_requirements")
    op.drop_table("case_requirements")
