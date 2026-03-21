from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.ui_automation import (
    MidsceneRunCreate,
    MidsceneRunListResponse,
    MidsceneRunOut,
    MidsceneRunnerHealth,
)
from app.services import midscene_run_service as midscene_svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=MidsceneRunnerHealth)
def midscene_health() -> MidsceneRunnerHealth:
    data = midscene_svc.runner_health()
    return MidsceneRunnerHealth(**data)


@router.post("/runs", response_model=MidsceneRunOut)
def create_midscene_run(
    body: MidsceneRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MidsceneRunOut:
    h = midscene_svc.runner_health()
    if body.runner == "playwright":
        if not h.get("playwright_ok"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=h.get("playwright_message") or "backend/playwright-runner 未就绪",
            )
    else:
        if not (
            h.get("node_found")
            and h.get("runner_dir_exists")
            and h.get("tsx_exists")
            and h.get("runner_script_exists")
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=h.get("message") or "backend/midscene-runner 未就绪",
            )
    run = midscene_svc.create_run_record(db, user_id=user.id, payload=body)
    payload_dict = body.model_dump()
    background_tasks.add_task(midscene_svc.background_execute, run.id, payload_dict)
    return midscene_svc.to_out(run)


@router.get("/runs", response_model=MidsceneRunListResponse)
def list_midscene_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MidsceneRunListResponse:
    items, total = midscene_svc.list_runs(db, user_id=user.id, page=page, page_size=page_size)
    return MidsceneRunListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=MidsceneRunOut)
def get_midscene_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MidsceneRunOut:
    run = midscene_svc.get_run(db, user_id=user.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return midscene_svc.to_out(run)


@router.get("/runs/{run_id}/report")
def download_report(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    p = midscene_svc.artifact_path(user.id, run_id, "report", db)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不可用")
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="text/html; charset=utf-8",
    )


@router.get("/runs/{run_id}/video")
def download_video(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    p = midscene_svc.artifact_path(user.id, run_id, "video", db)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不可用")
    ext = p.suffix.lower()
    media = "video/webm" if ext == ".webm" else "video/mp4" if ext == ".mp4" else "application/octet-stream"
    return FileResponse(path=str(p), filename=p.name, media_type=media)
