from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.managed_case import ManagedCase
from app.db.models.managed_requirement import ManagedRequirement
from app.db.models.midscene_run import MidsceneRun
from app.schemas.dashboard import (
    CaseExecutionBreakdown,
    DailyUiRunPoint,
    DashboardOverviewResponse,
    DashboardRecentRun,
    DashboardStatsBlock,
)
from app.services import midscene_run_service as midscene_svc

_TZ_SH = ZoneInfo("Asia/Shanghai")

_UI_STATUS_TEXT: dict[str, str] = {
    "pending": "等待中",
    "running": "执行中",
    "success": "通过",
    "failed": "失败",
}


def _short_start_url(start_url: str, max_len: int = 48) -> str:
    raw = (start_url or "").strip()
    if not raw:
        return ""
    p = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (p.netloc or p.path or raw).split("/")[0]
    path = (p.path or "").strip("/")
    hint = f"{host}/{path}" if path else host
    if len(hint) > max_len:
        return hint[: max_len - 1] + "…"
    return hint


def _run_title(instructions: str, start_url: str, max_len: int = 48) -> str:
    text = (instructions or "").strip()
    if text:
        one = text.splitlines()[0].strip()
        if one and one not in {"[", "[Playwright]"} and len(one) >= 2:
            if len(one) > max_len:
                return one[: max_len - 1] + "…"
            return one
    u = _short_start_url(start_url, max_len=max_len)
    if u:
        return u
    if (instructions or "").strip().startswith("[Playwright]"):
        return "Playwright 自动化"
    return "（未命名任务）"


def _local_day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=_TZ_SH)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def get_overview(db: Session, *, user_id: int) -> DashboardOverviewResponse:
    req_count = db.query(ManagedRequirement).filter(ManagedRequirement.user_id == user_id).count()

    case_total = (
        db.query(func.count(ManagedCase.id))
        .join(ManagedRequirement, ManagedCase.requirement_id == ManagedRequirement.id)
        .filter(ManagedRequirement.user_id == user_id)
        .scalar()
    )
    case_total = int(case_total or 0)

    rows = (
        db.query(ManagedCase.execution_status, func.count(ManagedCase.id))
        .join(ManagedRequirement, ManagedCase.requirement_id == ManagedRequirement.id)
        .filter(ManagedRequirement.user_id == user_id)
        .group_by(ManagedCase.execution_status)
        .all()
    )
    breakdown = CaseExecutionBreakdown()
    for status, cnt in rows:
        key = status or "not_executed"
        if key == "not_executed":
            breakdown.not_executed = int(cnt)
        elif key == "success":
            breakdown.success = int(cnt)
        elif key == "failed":
            breakdown.failed = int(cnt)
        elif key == "blocked":
            breakdown.blocked = int(cnt)

    succ, fail = breakdown.success, breakdown.failed
    if succ + fail > 0:
        pass_rate = round(100.0 * succ / (succ + fail), 1)
    else:
        pass_rate = None

    today_local = datetime.now(_TZ_SH).date()
    t_start, t_end = _local_day_bounds_utc(today_local)
    ui_today = (
        db.query(func.count(MidsceneRun.id))
        .filter(
            MidsceneRun.user_id == user_id,
            MidsceneRun.created_at >= t_start,
            MidsceneRun.created_at < t_end,
        )
        .scalar()
    )
    ui_today = int(ui_today or 0)

    ui_total = db.query(func.count(MidsceneRun.id)).filter(MidsceneRun.user_id == user_id).scalar()
    ui_total = int(ui_total or 0)

    series: list[DailyUiRunPoint] = []
    for i in range(6, -1, -1):
        d = today_local - timedelta(days=i)
        s, e = _local_day_bounds_utc(d)
        c = (
            db.query(func.count(MidsceneRun.id))
            .filter(
                MidsceneRun.user_id == user_id,
                MidsceneRun.created_at >= s,
                MidsceneRun.created_at < e,
            )
            .scalar()
        )
        series.append(DailyUiRunPoint(date=d.isoformat(), count=int(c or 0)))

    recent_items, _ = midscene_svc.list_runs(db, user_id=user_id, page=1, page_size=8)
    recent: list[DashboardRecentRun] = []
    for r in recent_items:
        st = r.status or "pending"
        recent.append(
            DashboardRecentRun(
                id=r.id,
                title=_run_title(r.instructions, r.start_url),
                status=st,
                status_text=_UI_STATUS_TEXT.get(st, st),
                run_at=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            )
        )

    stats = DashboardStatsBlock(
        requirement_count=req_count,
        case_count=case_total,
        case_pass_rate_percent=pass_rate,
        ui_runs_today=ui_today,
        ui_runs_total=ui_total,
    )

    return DashboardOverviewResponse(
        stats=stats,
        case_execution=breakdown,
        ui_runs_last_7_days=series,
        recent_ui_runs=recent,
    )
