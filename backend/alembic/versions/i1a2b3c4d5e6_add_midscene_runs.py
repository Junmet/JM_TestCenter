"""Midscene UI 自动化运行记录表"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "i1a2b3c4d5e6"
down_revision = "h0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "midscene_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, comment="运行 UUID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending", comment="pending/running/success/failed"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("model_name", sa.String(length=512, collation="utf8mb4_unicode_ci"), nullable=False, comment="模型名称"),
        sa.Column("model_family", sa.String(length=128, collation="utf8mb4_unicode_ci"), nullable=False, comment="模型系列"),
        sa.Column("model_base_url", sa.String(length=1024, collation="utf8mb4_unicode_ci"), nullable=False, comment="OpenAI 兼容 Base URL"),
        sa.Column("start_url", sa.Text(), nullable=False, comment="起始页面 URL"),
        sa.Column("instructions", sa.Text(), nullable=False, comment="自然语言指令"),
        sa.Column(
            "instruction_mode",
            sa.String(length=32),
            nullable=False,
            server_default="multi_line",
            comment="multi_line 或 single_block",
        ),
        sa.Column("headless", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="无头浏览器"),
        sa.Column("record_video", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否录屏"),
        sa.Column("report_file", sa.String(length=1024, collation="utf8mb4_unicode_ci"), nullable=True, comment="报告相对路径"),
        sa.Column("video_file", sa.String(length=1024, collation="utf8mb4_unicode_ci"), nullable=True, comment="视频相对路径"),
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
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始执行时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        comment="Midscene UI 自动化运行",
    )
    op.create_index("ix_midscene_runs_user_id", "midscene_runs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_midscene_runs_user_id", table_name="midscene_runs")
    op.drop_table("midscene_runs")
