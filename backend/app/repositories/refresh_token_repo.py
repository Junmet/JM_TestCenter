from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def revoke_active_tokens(self, db: Session, *, user_id: int) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.execute(stmt)

    def create_refresh_token(
        self,
        db: Session,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        return token

    def get_active_token_by_hash(self, db: Session, *, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

