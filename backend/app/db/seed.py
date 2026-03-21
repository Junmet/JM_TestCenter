"""
用于创建初始用户（开发环境）。

生产环境建议通过独立管理脚本/后台管理系统来完成。
"""

from app.core.security import hash_password
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models.user import User


def seed_default_user(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            # 为了兼容增加 is_admin 字段：默认 admin 一定要是管理员
            existing.password_hash = hash_password(password)
            existing.is_admin = True
            db.commit()
            return

        u = User(
            username=username,
            password_hash=hash_password(password),
            is_admin=True,
        )
        db.add(u)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    settings = get_settings()
    # 为避免 .env 里没有定义该字段导致报错，这里提供兜底
    username = getattr(settings, "DEFAULT_ADMIN_USERNAME", "admin")
    password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", "admin12345")
    seed_default_user(username=username, password=password)

