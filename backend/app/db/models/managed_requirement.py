from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ManagedRequirement(Base):
    __tablename__ = "managed_requirements"
    __table_args__ = {"comment": "用例管理-需求表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    code: Mapped[str] = mapped_column(
        String(64, collation="utf8mb4_unicode_ci"),
        nullable=False,
        unique=True,
        comment="需求编号",
    )
    title: Mapped[str] = mapped_column(
        String(255, collation="utf8mb4_unicode_ci"),
        nullable=False,
        comment="需求标题",
    )
    owner: Mapped[str] = mapped_column(
        String(64, collation="utf8mb4_unicode_ci"),
        nullable=False,
        server_default="当前用户",
        comment="负责人",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="active",
        comment="状态",
    )
    priority: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="p1",
        comment="优先级",
    )
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
