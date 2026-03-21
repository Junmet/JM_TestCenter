from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.db.session import get_db
from app.schemas.user import CreateUserRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter()


def get_user_service() -> UserService:
    return UserService()


@router.post("/admin/users", response_model=UserResponse)
def add_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        return user_service.create_user(db=db, username=payload.username, password=payload.password)
    except ValueError as e:
        # 统一把业务校验失败映射为 400/409
        msg = str(e)
        if "exists" in msg or "already exists" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

