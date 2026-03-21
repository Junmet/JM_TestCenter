from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.managed_case import ManagedCase
from app.db.models.managed_requirement import ManagedRequirement

# 用例执行状态（存库英文枚举）
EXECUTION_NOT_EXECUTED = "not_executed"
EXECUTION_SUCCESS = "success"
EXECUTION_FAILED = "failed"
EXECUTION_BLOCKED = "blocked"

EXECUTION_STATUS_LABELS: dict[str, str] = {
    EXECUTION_NOT_EXECUTED: "未执行",
    EXECUTION_SUCCESS: "成功",
    EXECUTION_FAILED: "失败",
    EXECUTION_BLOCKED: "阻塞",
}

# 需求进度（由用例执行状态推导）
PROGRESS_NOT_STARTED = "not_started"
PROGRESS_IN_PROGRESS = "in_progress"
PROGRESS_COMPLETED = "completed"

PROGRESS_LABELS: dict[str, str] = {
    PROGRESS_NOT_STARTED: "未开始",
    PROGRESS_IN_PROGRESS: "进行中",
    PROGRESS_COMPLETED: "已完成",
}


class CaseManagementService:
    @staticmethod
    def _now_text() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _execution_label(status: str) -> str:
        return EXECUTION_STATUS_LABELS.get(status, status)

    @staticmethod
    def _derive_progress_from_cases(case_rows: list[ManagedCase]) -> tuple[str, str]:
        """
        全部未执行 -> 未开始；全部已执行（无未执行）-> 已完成；否则 -> 进行中。
        无用例时视为未开始。
        """
        if not case_rows:
            return PROGRESS_NOT_STARTED, PROGRESS_LABELS[PROGRESS_NOT_STARTED]
        total = len(case_rows)
        not_exec = sum(1 for c in case_rows if (c.execution_status or EXECUTION_NOT_EXECUTED) == EXECUTION_NOT_EXECUTED)
        if not_exec == total:
            return PROGRESS_NOT_STARTED, PROGRESS_LABELS[PROGRESS_NOT_STARTED]
        if not_exec == 0:
            return PROGRESS_COMPLETED, PROGRESS_LABELS[PROGRESS_COMPLETED]
        return PROGRESS_IN_PROGRESS, PROGRESS_LABELS[PROGRESS_IN_PROGRESS]

    def list_requirements(
        self,
        *,
        db: Session,
        user_id: int,
        owner_username: str,
        page: int = 1,
        page_size: int = 10,
        keyword: str | None = None,
    ) -> tuple[int, list[dict]]:
        base_q = db.query(ManagedRequirement).filter(ManagedRequirement.user_id == user_id)
        kw = (keyword or "").strip()
        if kw:
            like = f"%{kw}%"
            base_q = base_q.filter(
                or_(ManagedRequirement.code.like(like), ManagedRequirement.title.like(like))
            )
        total = base_q.count()
        if total <= 0:
            return 0, []
        offset = max(0, (page - 1) * page_size)
        rows = (
            base_q.order_by(ManagedRequirement.updated_at.desc(), ManagedRequirement.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        req_ids = [r.id for r in rows]
        count_map: dict[int, int] = {rid: 0 for rid in req_ids}
        cases_by_req: dict[int, list[ManagedCase]] = {rid: [] for rid in req_ids}
        if req_ids:
            for c in db.query(ManagedCase).filter(ManagedCase.requirement_id.in_(req_ids)).all():
                count_map[c.requirement_id] = count_map.get(c.requirement_id, 0) + 1
                cases_by_req.setdefault(c.requirement_id, []).append(c)
        items: list[dict] = []
        for r in rows:
            case_rows = cases_by_req.get(r.id, [])
            progress_key, progress_text = self._derive_progress_from_cases(case_rows)
            items.append(
                {
                    "id": r.code,
                    "code": r.code,
                    "title": r.title,
                    "status": progress_key,
                    "statusText": progress_text,
                    "priority": r.priority,
                    "priorityText": r.priority.upper(),
                    "caseCount": count_map.get(r.id, 0),
                    "owner": owner_username,
                    "updatedAt": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else self._now_text(),
                }
            )
        return total, items

    def get_requirement_detail(self, *, db: Session, user_id: int, owner_username: str, req_code: str) -> dict | None:
        req = (
            db.query(ManagedRequirement)
            .filter(ManagedRequirement.user_id == user_id, ManagedRequirement.code == req_code)
            .first()
        )
        if not req:
            return None
        cases = (
            db.query(ManagedCase)
            .filter(ManagedCase.requirement_id == req.id)
            .order_by(ManagedCase.id.asc())
            .all()
        )
        progress_key, progress_text = self._derive_progress_from_cases(cases)
        return {
            "code": req.code,
            "title": req.title,
            "status": progress_key,
            "statusText": progress_text,
            "priorityText": req.priority.upper(),
            "owner": owner_username,
            "cases": [
                {
                    "id": c.id,
                    "code": c.case_code,
                    "name": c.name,
                    "typeText": c.type_text,
                    "priorityText": c.priority_text,
                    "executionStatus": c.execution_status or EXECUTION_NOT_EXECUTED,
                    "executionStatusText": self._execution_label(c.execution_status or EXECUTION_NOT_EXECUTED),
                    "lastRunAt": c.last_run_at,
                    "stepsText": c.steps_text or "",
                }
                for c in cases
            ],
        }

    def code_exists(self, *, db: Session, code: str, exclude_req_code: str | None = None) -> bool:
        q = db.query(ManagedRequirement).filter(ManagedRequirement.code == code)
        if exclude_req_code:
            q = q.filter(ManagedRequirement.code != exclude_req_code)
        return q.first() is not None

    def create_requirement(self, *, db: Session, user_id: int, owner_username: str, payload: dict) -> None:
        if self.code_exists(db=db, code=payload["code"]):
            raise ValueError("需求编号已存在")
        req = ManagedRequirement(
            user_id=user_id,
            code=payload["code"],
            title=payload["title"],
            owner=owner_username,
            priority=(payload.get("priority") or "p1").lower(),
            status="active",
        )
        db.add(req)
        db.flush()
        now_txt = self._now_text()
        for item in payload.get("cases") or []:
            db.add(
                ManagedCase(
                    requirement_id=req.id,
                    case_code=item["code"],
                    name=item["name"],
                    type_text="功能",
                    priority_text=item.get("priorityText") or "P1",
                    status_text="启用",
                    execution_status=EXECUTION_NOT_EXECUTED,
                    last_run_at=now_txt,
                    steps_text=item.get("stepsText") or "",
                )
            )
        db.commit()

    def update_requirement(self, *, db: Session, user_id: int, owner_username: str, req_code: str, payload: dict) -> None:
        req = (
            db.query(ManagedRequirement)
            .filter(ManagedRequirement.user_id == user_id, ManagedRequirement.code == req_code)
            .first()
        )
        if not req:
            raise ValueError("需求不存在")
        new_code = payload["code"].strip()
        if new_code != req.code and self.code_exists(db=db, code=new_code):
            raise ValueError("需求编号已存在")
        req.code = new_code
        req.title = payload["title"].strip()
        req.owner = owner_username
        db.commit()

    def update_requirement_priority(self, *, db: Session, user_id: int, req_code: str, priority: str) -> None:
        p = priority.lower().strip()
        if p not in ("p0", "p1", "p2"):
            raise ValueError("优先级仅支持 P0、P1、P2")
        req = (
            db.query(ManagedRequirement)
            .filter(ManagedRequirement.user_id == user_id, ManagedRequirement.code == req_code)
            .first()
        )
        if not req:
            raise ValueError("需求不存在")
        req.priority = p
        db.commit()

    def update_case_execution(
        self,
        *,
        db: Session,
        user_id: int,
        req_code: str,
        case_id: int,
        execution_status: str,
    ) -> None:
        es = execution_status.strip()
        allowed = {EXECUTION_NOT_EXECUTED, EXECUTION_SUCCESS, EXECUTION_FAILED, EXECUTION_BLOCKED}
        if es not in allowed:
            raise ValueError("无效的执行状态")
        req = (
            db.query(ManagedRequirement)
            .filter(ManagedRequirement.user_id == user_id, ManagedRequirement.code == req_code)
            .first()
        )
        if not req:
            raise ValueError("需求不存在")
        row = (
            db.query(ManagedCase)
            .filter(ManagedCase.id == case_id, ManagedCase.requirement_id == req.id)
            .first()
        )
        if not row:
            raise ValueError("用例不存在")
        row.execution_status = es
        row.last_run_at = self._now_text()
        db.commit()

    def delete_requirement(self, *, db: Session, user_id: int, req_code: str) -> None:
        req = (
            db.query(ManagedRequirement)
            .filter(ManagedRequirement.user_id == user_id, ManagedRequirement.code == req_code)
            .first()
        )
        if not req:
            raise ValueError("需求不存在")
        db.query(ManagedCase).filter(ManagedCase.requirement_id == req.id).delete(synchronize_session=False)
        db.delete(req)
        db.commit()
