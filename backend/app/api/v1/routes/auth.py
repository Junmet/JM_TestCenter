from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return auth_service.login(db=db, username=payload.username, password=payload.password)
    except ValueError as e:
        # 统一把认证失败映射为 401
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

