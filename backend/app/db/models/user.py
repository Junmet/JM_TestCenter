from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    username = Column(
        String(64, collation="utf8mb4_unicode_ci"),
        unique=True,
        nullable=False,
        comment="用户名",
    )
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    is_admin = Column(Boolean, nullable=False, server_default="0", comment="是否管理员")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    # keeps mapper consistent with SQLAlchemy defaults
    __mapper_args__ = {"eager_defaults": True}

