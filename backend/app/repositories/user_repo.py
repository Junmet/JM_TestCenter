from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def get_by_username(self, db: Session, *, username: str) -> User | None:
        stmt = select(User).where(User.username == username).limit(1)
        return db.execute(stmt).scalar_one_or_none()

    def create_user(self, db: Session, *, username: str, password_hash: str, is_admin: bool) -> User:
        user = User(username=username, password_hash=password_hash, is_admin=is_admin)
        db.add(user)
        db.flush()  # 获取自增主键
        return user

