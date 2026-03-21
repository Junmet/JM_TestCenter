from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CaseRequirement(Base):
    __tablename__ = "case_requirements"
    __table_args__ = {"comment": "用例生成-需求文档记录"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="上传用户ID",
    )
    source_name: Mapped[str] = mapped_column(
        String(255, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="原始文件名",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="generated",
        comment="状态: generated/failed",
    )
    context_summary: Mapped[str] = mapped_column(Text, nullable=False, comment="文档摘要")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
