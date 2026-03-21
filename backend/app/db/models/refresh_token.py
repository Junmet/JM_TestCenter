from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"comment": "刷新令牌表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="用户ID",
    )
    token_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        comment="刷新令牌hash（sha256 hex）",
    )  # sha256 hex
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    revoked_at = Column(DateTime(timezone=True), nullable=True, comment="注销时间")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    user = relationship("User", backref="refresh_tokens")

