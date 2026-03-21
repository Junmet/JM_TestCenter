from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ManagedCase(Base):
    __tablename__ = "managed_cases"
    __table_args__ = {"comment": "用例管理-用例表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("managed_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="需求ID",
    )
    case_code: Mapped[str] = mapped_column(
        String(64, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="用例编号",
    )
    name: Mapped[str] = mapped_column(
        String(255, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="用例名称",
    )
    steps_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="用例步骤文本",
    )
    type_text: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="功能",
        comment="类型",
    )
    priority_text: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="P1",
        comment="优先级文本",
    )
    status_text: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="启用",
        comment="状态文本（遗留字段，界面已改用执行状态）",
    )
    execution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="not_executed",
        comment="执行状态：not_executed/success/failed/blocked",
    )
    last_run_at: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="",
        comment="最后执行时间文本",
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
