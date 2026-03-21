from datetime import datetime

from pydantic import BaseModel


class GeneratedCaseItem(BaseModel):
    id: int
    case_code: str
    priority: str
    module: str
    title: str
    summary: str
    preconditions: str
    steps: list[str]
    expected: list[str]
    actual_result: str
    test_type: str
    data: str
    remarks: str
    confirmed: bool


class CaseGenerationResponse(BaseModel):
    requirement_id: int
    source_name: str
    created_at: datetime
    cases: list[GeneratedCaseItem]


class ConfirmCasesRequest(BaseModel):
    case_ids: list[int]


class CaseGenerationHistoryItem(BaseModel):
    requirement_id: int
    source_name: str
    status: str
    case_count: int
    confirmed_count: int
    created_at: datetime


class CaseGenerationHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CaseGenerationHistoryItem]
