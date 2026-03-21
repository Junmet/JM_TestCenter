from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard_service import get_overview

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardOverviewResponse:
    """控制台聚合：用例管理统计、UI 自动化趋势与最近任务。"""
    return get_overview(db, user_id=current_user.id)
