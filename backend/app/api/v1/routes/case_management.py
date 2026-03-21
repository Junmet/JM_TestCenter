from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.case_management import (
    CodeExistsResponse,
    CreateRequirementRequest,
    RequirementDetailResponse,
    RequirementListResponse,
    UpdateCaseExecutionRequest,
    UpdatePriorityRequest,
    UpdateRequirementRequest,
)
from app.services.case_management_service import CaseManagementService

router = APIRouter()


def get_service() -> CaseManagementService:
    return CaseManagementService()


@router.get("/requirements", response_model=RequirementListResponse)
def list_requirements(
    page: int = Query(1),
    page_size: int = Query(10),
    q: str | None = Query(None, description="按需求编号/标题模糊搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> RequirementListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 50))
    total, requirements = service.list_requirements(
        db=db,
        user_id=current_user.id,
        owner_username=current_user.username,
        page=safe_page,
        page_size=safe_page_size,
        keyword=q,
    )
    return RequirementListResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        requirements=requirements,
    )


@router.get("/requirements/code-exists", response_model=CodeExistsResponse)
def check_code_exists(
    code: str = Query(...),
    exclude_code: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> CodeExistsResponse:
    return CodeExistsResponse(exists=service.code_exists(db=db, code=code, exclude_req_code=exclude_code))


@router.get("/requirements/{req_code}", response_model=RequirementDetailResponse)
def get_requirement_detail(
    req_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> RequirementDetailResponse:
    data = service.get_requirement_detail(
        db=db, user_id=current_user.id, owner_username=current_user.username, req_code=req_code
    )
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="需求不存在")
    return RequirementDetailResponse(**data)


@router.post("/requirements")
def create_requirement(
    payload: CreateRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> dict:
    try:
        service.create_requirement(
            db=db,
            user_id=current_user.id,
            owner_username=current_user.username,
            payload=payload.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"ok": True}


@router.put("/requirements/{req_code}")
def update_requirement(
    req_code: str,
    payload: UpdateRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> dict:
    try:
        service.update_requirement(
            db=db,
            user_id=current_user.id,
            owner_username=current_user.username,
            req_code=req_code,
            payload=payload.model_dump(),
        )
    except ValueError as e:
        detail = str(e)
        status_code = status.HTTP_409_CONFLICT if "已存在" in detail else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    return {"ok": True}


@router.patch("/requirements/{req_code}/priority")
def update_requirement_priority(
    req_code: str,
    payload: UpdatePriorityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> dict:
    try:
        service.update_requirement_priority(
            db=db, user_id=current_user.id, req_code=req_code, priority=payload.priority
        )
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_404_NOT_FOUND if "不存在" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail)
    return {"ok": True}


@router.patch("/requirements/{req_code}/cases/{case_id}/execution")
def update_case_execution(
    req_code: str,
    case_id: int,
    payload: UpdateCaseExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> dict:
    try:
        service.update_case_execution(
            db=db,
            user_id=current_user.id,
            req_code=req_code,
            case_id=case_id,
            execution_status=payload.execution_status,
        )
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_404_NOT_FOUND if "不存在" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail)
    return {"ok": True}


@router.delete("/requirements/{req_code}")
def delete_requirement(
    req_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseManagementService = Depends(get_service),
) -> dict:
    try:
        service.delete_requirement(db=db, user_id=current_user.id, req_code=req_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"ok": True}
