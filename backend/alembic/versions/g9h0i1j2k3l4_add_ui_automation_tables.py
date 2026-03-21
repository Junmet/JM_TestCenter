from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "g9h0i1j2k3l4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return set(insp.get_table_names())


def upgrade() -> None:
    tables = _table_names()

    if "ui_automation_cases" not in tables:
        op.create_table(
            "ui_automation_cases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户"),
            sa.Column("name", sa.String(length=200, collation="utf8mb4_unicode_ci"), nullable=False, comment="用例名称"),
            sa.Column("description", sa.Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="描述"),
            sa.Column(
                "scenario_type",
                sa.String(length=64),
                server_default="baidu_search",
                nullable=False,
                comment="场景类型",
            ),
            sa.Column("config_json", sa.Text(collation="utf8mb4_unicode_ci"), nullable=False, comment="场景配置 JSON"),
            sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False, comment="是否启用"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_ui_automation_cases_user_id_users")),
            sa.PrimaryKeyConstraint("id"),
            comment="UI自动化用例",
        )
        op.create_index(op.f("ix_ui_automation_cases_user_id"), "ui_automation_cases", ["user_id"], unique=False)

    tables = _table_names()
    if "ui_automation_runs" not in tables:
        op.create_table(
            "ui_automation_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("ok", sa.Boolean(), nullable=False, comment="是否成功"),
            sa.Column(
                "message",
                sa.String(length=2000, collation="utf8mb4_unicode_ci"),
                server_default="",
                nullable=False,
            ),
            sa.Column("final_url", sa.String(length=2000), server_default="", nullable=False),
            sa.Column(
                "page_title",
                sa.String(length=500, collation="utf8mb4_unicode_ci"),
                server_default="",
                nullable=False,
            ),
            sa.Column(
                "result_preview",
                sa.Text(collation="utf8mb4_unicode_ci"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["case_id"], ["ui_automation_cases.id"], name=op.f("fk_ui_automation_runs_case_id_ui_automation_cases")
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_ui_automation_runs_user_id_users")),
            sa.PrimaryKeyConstraint("id"),
            comment="UI自动化执行记录",
        )
        op.create_index(op.f("ix_ui_automation_runs_case_id"), "ui_automation_runs", ["case_id"], unique=False)
        op.create_index(op.f("ix_ui_automation_runs_user_id"), "ui_automation_runs", ["user_id"], unique=False)


def downgrade() -> None:
    tables = _table_names()
    if "ui_automation_runs" in tables:
        op.drop_table("ui_automation_runs")
    tables = _table_names()
    if "ui_automation_cases" in tables:
        op.drop_table("ui_automation_cases")
