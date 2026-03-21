import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# 为避免 bcrypt 依赖在不同环境下出现兼容问题，这里改用 pbkdf2_sha256。
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: int, username: str) -> Tuple[str, int]:
    settings = get_settings()
    expire_minutes = settings.JWT_ACCESS_EXPIRE_MINUTES
    now = _utcnow()
    exp = now + timedelta(minutes=expire_minutes)

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(to_encode, settings.JWT_ACCESS_SECRET, algorithm=settings.JWT_ALG)
    expires_in = int((exp - now).total_seconds())
    return token, expires_in


def generate_refresh_token() -> str:
    # 作为“随机字符串 token”，真正持久化时只存 hash，避免 DB 泄露导致 token 直接可用
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    settings = get_settings()
    return _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    解码并校验 access token（包含 exp/iss）。
    返回 token payload。
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError as e:
        raise ValueError("Invalid or expired access token") from e

    if payload.get("iss") != settings.JWT_ISSUER:
        raise ValueError("Invalid token issuer")
    if "sub" not in payload:
        raise ValueError("Token missing subject")
    return payload

