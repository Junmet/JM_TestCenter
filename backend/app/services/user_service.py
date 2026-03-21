from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()

    def create_user(
        self,
        db: Session,
        *,
        username: str,
        password: str,
    ) -> dict:
        # 新用户默认非管理员
        if self.user_repo.get_by_username(db, username=username):
            raise ValueError("Username already exists")

        password_hash = hash_password(password)
        user = self.user_repo.create_user(
            db,
            username=username,
            password_hash=password_hash,
            is_admin=False,
        )
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username, "is_admin": user.is_admin}

