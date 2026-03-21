from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import create_access_token, generate_refresh_token, hash_token, refresh_token_expiry, verify_password
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.refresh_repo = RefreshTokenRepository()

    def login(self, *, db: Session, username: str, password: str) -> dict:
        user = self.user_repo.get_by_username(db, username=username)
        if not user:
            raise ValueError("Invalid username or password")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid username or password")

        # access token
        access_token, expires_in = create_access_token(user_id=user.id, username=user.username)

        # refresh token (random string stored only as hash)
        refresh_token = generate_refresh_token()
        token_hash = hash_token(refresh_token)
        expires_at: datetime = refresh_token_expiry()

        # revoke old refresh tokens (single active token strategy)
        self.refresh_repo.revoke_active_tokens(db, user_id=user.id)
        self.refresh_repo.create_refresh_token(
            db,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.commit()

        return {
            "token_type": "bearer",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "user": {"id": user.id, "username": user.username},
        }

