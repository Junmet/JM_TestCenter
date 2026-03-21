import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.case_gen import (
    CaseGenerationHistoryItem,
    CaseGenerationHistoryResponse,
    CaseGenerationResponse,
    ConfirmCasesRequest,
    GeneratedCaseItem,
)
from app.services.case_gen_service import CaseGenerationService
from app.utils.generation_errors import PUBLIC_GENERATION_FAILED, log_generation_failure_hints

router = APIRouter()
logger = logging.getLogger(__name__)


def get_case_gen_service() -> CaseGenerationService:
    return CaseGenerationService()


@router.post("/generate", response_model=CaseGenerationResponse)
def upload_and_generate_cases(
    file: UploadFile = File(...),
    max_cases: int = Form(30),
    batch_size: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseGenerationService = Depends(get_case_gen_service),
) -> CaseGenerationResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件名不能为空")
    suffix = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if suffix not in {"txt", "md", "markdown", "docx", "pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 txt/md/markdown/docx/pdf 文件",
        )
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空")
    safe_max_cases = max(10, min(max_cases, 200))
    safe_batch_size = batch_size
    if safe_batch_size is None:
        safe_batch_size = max(10, min(20, safe_max_cases // 6 if safe_max_cases >= 60 else 10))
    safe_batch_size = max(5, min(safe_batch_size, 30))
    try:
        requirement, rows = service.generate_from_upload(
            db=db,
            user_id=current_user.id,
            filename=file.filename,
            content=raw,
            max_cases=safe_max_cases,
            batch_size=safe_batch_size,
        )
    except Exception as e:
        logger.exception("case-gen generate failed: %s", e)
        log_generation_failure_hints(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PUBLIC_GENERATION_FAILED,
        )
    return CaseGenerationResponse(
        requirement_id=requirement.id,
        source_name=requirement.source_name,
        created_at=requirement.created_at,
        cases=[
            GeneratedCaseItem(
                id=r.id,
                case_code=r.case_code,
                priority=r.priority,
                module=r.module,
                title=r.title,
                summary=r.summary,
                preconditions=r.preconditions,
                steps=r.steps or [],
                expected=r.expected or [],
                actual_result=r.actual_result,
                test_type=r.test_type,
                data=r.data,
                remarks=r.remarks,
                confirmed=r.confirmed,
            )
            for r in rows
        ],
    )


@router.get("/requirements/{requirement_id}/cases", response_model=CaseGenerationResponse)
def get_generated_cases(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseGenerationService = Depends(get_case_gen_service),
) -> CaseGenerationResponse:
    requirement, rows = service.get_cases_by_requirement(
        db=db,
        requirement_id=requirement_id,
        user_id=current_user.id,
    )
    if not requirement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="需求记录不存在")
    return CaseGenerationResponse(
        requirement_id=requirement.id,
        source_name=requirement.source_name,
        created_at=requirement.created_at,
        cases=[
            GeneratedCaseItem(
                id=r.id,
                case_code=r.case_code,
                priority=r.priority,
                module=r.module,
                title=r.title,
                summary=r.summary,
                preconditions=r.preconditions,
                steps=r.steps or [],
                expected=r.expected or [],
                actual_result=r.actual_result,
                test_type=r.test_type,
                data=r.data,
                remarks=r.remarks,
                confirmed=r.confirmed,
            )
            for r in rows
        ],
    )


@router.post("/requirements/{requirement_id}/confirm")
def confirm_generated_cases(
    requirement_id: int,
    payload: ConfirmCasesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseGenerationService = Depends(get_case_gen_service),
) -> dict:
    updated = service.confirm_cases(
        db=db,
        requirement_id=requirement_id,
        user_id=current_user.id,
        case_ids=payload.case_ids,
    )
    return {"updated": updated}


@router.get("/histories", response_model=CaseGenerationHistoryResponse)
def list_generation_histories(
    page: int = Query(1),
    page_size: int = Query(10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseGenerationService = Depends(get_case_gen_service),
) -> CaseGenerationHistoryResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 50))
    total, items = service.list_histories(
        db=db,
        user_id=current_user.id,
        page=safe_page,
        page_size=safe_page_size,
    )
    return CaseGenerationHistoryResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=[
            CaseGenerationHistoryItem(
                requirement_id=i["requirement_id"],
                source_name=i["source_name"],
                status=i["status"],
                case_count=i["case_count"],
                confirmed_count=i["confirmed_count"],
                created_at=i["created_at"],
            )
            for i in items
        ]
    )


@router.delete("/histories/{requirement_id}")
def delete_generation_history(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: CaseGenerationService = Depends(get_case_gen_service),
) -> dict:
    ok = service.delete_history(db=db, user_id=current_user.id, requirement_id=requirement_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")
    return {"ok": True}
