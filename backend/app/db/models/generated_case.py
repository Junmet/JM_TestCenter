from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedCase(Base):
    __tablename__ = "generated_cases"
    __table_args__ = {"comment": "用例生成-测试用例记录"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("case_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="需求记录ID",
    )
    case_code: Mapped[str] = mapped_column(
        String(64, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="用例编号",
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="P2", comment="优先级")
    module: Mapped[str] = mapped_column(
        String(128, collation="utf8mb4_unicode_ci"),
        nullable=False,
        server_default="",
        comment="模块",
    )
    title: Mapped[str] = mapped_column(
        String(255, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="测试标题",
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="摘要")
    preconditions: Mapped[str] = mapped_column(Text, nullable=False, comment="前置条件")
    steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="测试步骤")
    expected: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="期望结果")
    actual_result: Mapped[str] = mapped_column(Text, nullable=False, comment="实际结果")
    test_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="", comment="测试类型")
    data: Mapped[str] = mapped_column(Text, nullable=False, comment="测试数据")
    remarks: Mapped[str] = mapped_column(Text, nullable=False, comment="备注")
    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="是否确认",
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
