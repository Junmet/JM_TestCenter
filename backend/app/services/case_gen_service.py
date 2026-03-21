from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.db.models.case_requirement import CaseRequirement
from app.db.models.generated_case import GeneratedCase


class CaseGenerationService:
    def __init__(self) -> None:
        # 与 midscene-runner / playwright-runner 一致：testcase 位于 backend/testcase
        self._testcase_root = Path(__file__).resolve().parents[2] / "testcase"

    @staticmethod
    def _ensure_langchain_compat() -> None:
        try:
            import langchain  # type: ignore

            if not hasattr(langchain, "verbose"):
                setattr(langchain, "verbose", False)
            if not hasattr(langchain, "debug"):
                setattr(langchain, "debug", False)
            if not hasattr(langchain, "llm_cache"):
                setattr(langchain, "llm_cache", None)
        except Exception:
            pass

    def generate_from_upload(
        self,
        *,
        db: Session,
        user_id: int,
        filename: str,
        content: bytes,
        max_cases: int = 30,
        batch_size: int = 10,
        max_chars: int = 15000,
        language: str | None = None,
    ) -> tuple[CaseRequirement, list[GeneratedCase]]:
        parse_document, load_config, build_llm, generate_outline, generate_cases_batch = (
            self._load_testcase_modules()
        )
        self._ensure_langchain_compat()
        # 强制加载 testcase 目录下的 .env，确保 DeepSeek 配置可用
        load_dotenv(self._testcase_root / ".env", override=True)
        safe_name = os.path.basename(filename) or "requirement.txt"
        suffix = Path(safe_name).suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            tmp_path = Path(f.name)
            f.write(content)

        try:
            parsed = parse_document(tmp_path)
            doc_text = parsed.text[:max_chars]
            cfg = load_config(override_language=language)
            llm = build_llm(cfg)
            outline = generate_outline(
                cfg=cfg,
                llm=llm,
                source_name=safe_name,
                document_text=doc_text,
            )

            all_cases = []
            existing_titles: list[str] = []
            seen_titles: set[str] = set()
            tp_idx = 0
            max_batches_limit = max(3, (max_cases // max(1, batch_size)) * 3)
            total_batches = 0
            zero_new_batches = 0

            while (
                len(all_cases) < max_cases
                and outline.test_points
                and total_batches < max_batches_limit
            ):
                test_point = outline.test_points[tp_idx % len(outline.test_points)]
                tp_idx += 1
                remaining = max_cases - len(all_cases)
                cur_batch_size = min(batch_size, remaining)
                total_batches += 1
                batch = generate_cases_batch(
                    cfg=cfg,
                    llm=llm,
                    source_name=safe_name,
                    context_summary=outline.context_summary,
                    test_point=test_point,
                    batch_size=cur_batch_size,
                    existing_titles=existing_titles,
                )
                new_count = 0
                for tc in batch.test_cases:
                    key = (tc.title or "").strip() or f"ID:{tc.id}".strip()
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)
                    all_cases.append(tc)
                    if tc.title:
                        existing_titles.append(tc.title)
                    new_count += 1
                    if len(all_cases) >= max_cases:
                        break
                if new_count == 0:
                    zero_new_batches += 1
                    if zero_new_batches >= 5:
                        break
                else:
                    zero_new_batches = 0

            requirement = CaseRequirement(
                user_id=user_id,
                source_name=safe_name,
                status="generated",
                context_summary=outline.context_summary,
            )
            db.add(requirement)
            db.flush()

            rows: list[GeneratedCase] = []
            for tc in all_cases:
                row = GeneratedCase(
                    requirement_id=requirement.id,
                    case_code=tc.id,
                    priority=tc.priority or "P2",
                    module=tc.module or "",
                    title=tc.title or "",
                    summary=tc.summary or "",
                    preconditions=tc.preconditions or "",
                    steps=tc.steps or [],
                    expected=tc.expected or [],
                    actual_result=tc.actual_result or "",
                    test_type=tc.test_type or "",
                    data=tc.data or "",
                    remarks=tc.remarks or "",
                    confirmed=False,
                )
                rows.append(row)
                db.add(row)

            db.commit()
            db.refresh(requirement)
            return requirement, rows
        except Exception as e:
            db.rollback()
            failed = CaseRequirement(
                user_id=user_id,
                source_name=safe_name,
                status="failed",
                context_summary="",
                error_message=str(e),
            )
            db.add(failed)
            db.commit()
            raise
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def get_cases_by_requirement(
        self,
        *,
        db: Session,
        requirement_id: int,
        user_id: int,
    ) -> tuple[CaseRequirement | None, list[GeneratedCase]]:
        requirement = (
            db.query(CaseRequirement)
            .filter(CaseRequirement.id == requirement_id, CaseRequirement.user_id == user_id)
            .first()
        )
        if not requirement:
            return None, []
        rows = (
            db.query(GeneratedCase)
            .filter(GeneratedCase.requirement_id == requirement.id)
            .order_by(GeneratedCase.id.asc())
            .all()
        )
        return requirement, rows

    def confirm_cases(
        self,
        *,
        db: Session,
        requirement_id: int,
        user_id: int,
        case_ids: list[int],
    ) -> int:
        requirement = (
            db.query(CaseRequirement)
            .filter(CaseRequirement.id == requirement_id, CaseRequirement.user_id == user_id)
            .first()
        )
        if not requirement:
            return 0
        if not case_ids:
            return 0
        updated = (
            db.query(GeneratedCase)
            .filter(GeneratedCase.requirement_id == requirement_id, GeneratedCase.id.in_(case_ids))
            .update({"confirmed": True}, synchronize_session=False)
        )
        db.commit()
        return int(updated or 0)

    def list_histories(
        self,
        *,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[dict]]:
        total = db.query(CaseRequirement).filter(CaseRequirement.user_id == user_id).count()
        if total <= 0:
            return 0, []
        offset = max(0, (page - 1) * page_size)
        requirements = (
            db.query(CaseRequirement)
            .filter(CaseRequirement.user_id == user_id)
            .order_by(CaseRequirement.created_at.desc(), CaseRequirement.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        if not requirements:
            return total, []
        req_ids = [r.id for r in requirements]
        case_rows = db.query(GeneratedCase).filter(GeneratedCase.requirement_id.in_(req_ids)).all()
        stat_map: dict[int, dict[str, int]] = {}
        for c in case_rows:
            cur = stat_map.setdefault(c.requirement_id, {"case_count": 0, "confirmed_count": 0})
            cur["case_count"] += 1
            if c.confirmed:
                cur["confirmed_count"] += 1
        return total, [
            {
                "requirement_id": r.id,
                "source_name": r.source_name,
                "status": r.status,
                "case_count": stat_map.get(r.id, {}).get("case_count", 0),
                "confirmed_count": stat_map.get(r.id, {}).get("confirmed_count", 0),
                "created_at": r.created_at,
            }
            for r in requirements
        ]

    def delete_history(self, *, db: Session, user_id: int, requirement_id: int) -> bool:
        requirement = (
            db.query(CaseRequirement)
            .filter(CaseRequirement.id == requirement_id, CaseRequirement.user_id == user_id)
            .first()
        )
        if not requirement:
            return False
        db.delete(requirement)
        db.commit()
        return True

    def _load_testcase_modules(self):
        # 复用 testcase 目录里的生成逻辑
        if str(self._testcase_root) not in sys.path:
            sys.path.insert(0, str(self._testcase_root))
        parsers = importlib.import_module("src.parsers")
        config = importlib.import_module("src.config")
        llm = importlib.import_module("src.llm")
        return (
            getattr(parsers, "parse_document"),
            getattr(config, "load_config"),
            getattr(llm, "build_llm"),
            getattr(llm, "generate_outline"),
            getattr(llm, "generate_cases_batch"),
        )
