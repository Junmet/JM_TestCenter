from pydantic import BaseModel, ConfigDict, Field


class ManagedCaseItem(BaseModel):
    id: int
    code: str
    name: str
    typeText: str
    priorityText: str
    executionStatus: str
    executionStatusText: str
    lastRunAt: str
    stepsText: str


class ManagedRequirementItem(BaseModel):
    id: str
    code: str
    title: str
    status: str
    statusText: str
    priority: str
    priorityText: str
    caseCount: int
    owner: str
    updatedAt: str


class RequirementListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    requirements: list[ManagedRequirementItem]


class RequirementDetailResponse(BaseModel):
    code: str
    title: str
    status: str
    statusText: str
    priorityText: str
    owner: str
    cases: list[ManagedCaseItem]


class CreateManagedCaseInput(BaseModel):
    code: str
    name: str
    priorityText: str = "P1"
    stepsText: str = ""


class CreateRequirementRequest(BaseModel):
    code: str
    title: str
    owner: str = "当前用户"
    priority: str = "p1"
    cases: list[CreateManagedCaseInput]


class UpdateRequirementRequest(BaseModel):
    code: str
    title: str
    owner: str | None = None


class UpdatePriorityRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    priority: str = Field(..., description="p0 / p1 / p2")


class UpdateCaseExecutionRequest(BaseModel):
    execution_status: str


class CodeExistsResponse(BaseModel):
    exists: bool
