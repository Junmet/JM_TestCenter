from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MidsceneRun(Base):
    __tablename__ = "midscene_runs"
    __table_args__ = {"comment": "Midscene UI 自动化运行"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="运行 UUID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="pending",
        comment="pending/running/success/failed",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    model_name: Mapped[str] = mapped_column(String(512, collation="utf8mb4_unicode_ci"), nullable=False)
    model_family: Mapped[str] = mapped_column(String(128, collation="utf8mb4_unicode_ci"), nullable=False)
    model_base_url: Mapped[str] = mapped_column(String(1024, collation="utf8mb4_unicode_ci"), nullable=False)
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    instruction_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="multi_line",
        comment="multi_line 或 single_block",
    )
    headless: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    record_video: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    report_file: Mapped[str | None] = mapped_column(String(1024, collation="utf8mb4_unicode_ci"), nullable=True)
    video_file: Mapped[str | None] = mapped_column(String(1024, collation="utf8mb4_unicode_ci"), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
