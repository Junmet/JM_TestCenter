from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardStatsBlock(BaseModel):
    requirement_count: int = Field(..., description="当前用户的测试需求数")
    case_count: int = Field(..., description="当前用户名下用例总数")
    case_pass_rate_percent: float | None = Field(
        None, description="用例通过率：成功/(成功+失败)，无已执行结果时为 null"
    )
    ui_runs_today: int = Field(..., description="今日 UI 自动化执行次数（按服务器时区 Asia/Shanghai 自然日）")
    ui_runs_total: int = Field(..., description="UI 自动化累计执行次数")


class CaseExecutionBreakdown(BaseModel):
    not_executed: int = 0
    success: int = 0
    failed: int = 0
    blocked: int = 0


class DailyUiRunPoint(BaseModel):
    date: str = Field(..., description="自然日 YYYY-MM-DD（Asia/Shanghai）")
    count: int = 0


class DashboardRecentRun(BaseModel):
    id: str
    title: str
    status: str
    status_text: str
    run_at: str


class DashboardOverviewResponse(BaseModel):
    stats: DashboardStatsBlock
    case_execution: CaseExecutionBreakdown
    ui_runs_last_7_days: list[DailyUiRunPoint]
    recent_ui_runs: list[DashboardRecentRun]
