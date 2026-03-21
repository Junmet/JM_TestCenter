from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.midscene_run import MidsceneRun
from app.schemas.ui_automation import MidsceneRunCreate, MidsceneRunOut


def background_execute(run_id: str, payload_dict: dict) -> None:
    """供 FastAPI BackgroundTasks 调用；独立 Session，避免请求结束后会话关闭。"""
    from app.db.session import SessionLocal

    payload = MidsceneRunCreate(**payload_dict)
    db = SessionLocal()
    try:
        if payload.runner == "playwright":
            run_playwright_sync(db=db, run_id=run_id, payload=payload)
        else:
            run_midscene_sync(
                db=db,
                run_id=run_id,
                api_key=payload.model.api_key,
                payload=payload,
            )
    finally:
        db.close()

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _artifact_root() -> Path:
    return get_settings().MIDSCENE_ARTIFACTS_DIR.resolve()


def _safe_join(run_id: str, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = (_artifact_root() / run_id / rel).resolve()
    root = _artifact_root() / run_id
    if not str(p).startswith(str(root.resolve())):
        return None
    return p


def _runner_cmd() -> tuple[list[str], Path]:
    settings = get_settings()
    runner = settings.MIDSCENE_RUNNER_DIR.resolve()
    tsx = runner / "node_modules" / "tsx" / "dist" / "cli.mjs"
    script = runner / "src" / "run.ts"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 Node.js（node），请先安装 Node 18+ 并在 PATH 中可用")
    if not tsx.is_file():
        raise RuntimeError(
            f"未找到 tsx，请在 {runner} 执行 npm install（midscene-runner）",
        )
    if not script.is_file():
        raise RuntimeError(f"未找到 midscene 运行脚本: {script}")
    return [node, str(tsx), str(script)], runner


def _playwright_runner_cmd() -> tuple[list[str], Path]:
    settings = get_settings()
    runner = settings.PLAYWRIGHT_RUNNER_DIR.resolve()
    tsx = runner / "node_modules" / "tsx" / "dist" / "cli.mjs"
    script = runner / "src" / "run.ts"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 Node.js（node），请先安装 Node 18+ 并在 PATH 中可用")
    if not tsx.is_file():
        raise RuntimeError(
            f"未找到 tsx，请在 {runner} 执行 npm install（playwright-runner）",
        )
    if not script.is_file():
        raise RuntimeError(f"未找到 playwright 运行脚本: {script}")
    return [node, str(tsx), str(script)], runner


def _read_result_json(work_dir: Path) -> dict | None:
    path = work_dir / "result.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_midscene_sync(
    *,
    db: Session,
    run_id: str,
    api_key: str,
    payload: MidsceneRunCreate,
) -> None:
    """在后台线程中执行；api_key 不落库。"""
    settings = get_settings()
    runner = settings.MIDSCENE_RUNNER_DIR.resolve()
    work_dir = (settings.MIDSCENE_ARTIFACTS_DIR / run_id).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    run = db.get(MidsceneRun, run_id)
    if not run:
        logger.error("midscene run %s missing", run_id)
        return

    if payload.runner != "midscene":
        run.status = "failed"
        run.error_message = "内部错误：非 Midscene 任务不应进入 run_midscene_sync"
        run.finished_at = _utcnow()
        db.commit()
        return

    key = (api_key or "").strip()
    if not key:
        run.status = "failed"
        run.error_message = "API Key 为空，无法调用模型"
        run.finished_at = _utcnow()
        db.commit()
        return

    run.status = "running"
    run.started_at = _utcnow()
    db.commit()

    env = os.environ.copy()
    base = payload.model.base_url.rstrip("/")

    # Midscene：非 default 意图可能读 MIDSCENE_OPENAI_*；default 回退逻辑读 LEGACY 的 OPENAI_*（见 decide-model-config.js）
    env["MIDSCENE_OPENAI_BASE_URL"] = base
    env["MIDSCENE_OPENAI_API_KEY"] = key
    env["OPENAI_BASE_URL"] = base
    env["OPENAI_API_KEY"] = key
    env["MIDSCENE_MODEL_NAME"] = payload.model.name
    env["MIDSCENE_VL_MODE"] = payload.model.family.strip()
    env["MIDSCENE_WORK_DIR"] = str(work_dir)
    env["MIDSCENE_AI_ACTION_TIMEOUT_MS"] = str(max(0, int(settings.MIDSCENE_AI_ACTION_TIMEOUT_MS)))
    rcl = int(settings.MIDSCENE_REPLANNING_CYCLE_LIMIT)
    if rcl > 0:
        env["MIDSCENE_REPLANNING_CYCLE_LIMIT"] = str(rcl)
    cfg: dict = {
        "startUrl": payload.start_url,
        "instructionMode": payload.instruction_mode,
        "instructions": payload.instructions or "",
        "headless": payload.headless,
        "recordVideo": payload.record_video,
        "stepGapMs": payload.step_gap_ms,
        "stableWaitAfterStep": payload.stable_wait_after_step,
    }
    if payload.execution_steps and len(payload.execution_steps) > 0:
        cfg["executionSteps"] = payload.execution_steps
    env["MIDSCENE_CONFIG_JSON"] = json.dumps(cfg, ensure_ascii=False)
    if settings.MIDSCENE_SETTLE_NETWORK_IDLE:
        env["MIDSCENE_SETTLE_NETWORK_IDLE"] = "1"

    cmd, _runner_root = _runner_cmd()
    run_timeout = max(60, int(settings.MIDSCENE_RUN_TIMEOUT_SECONDS))
    try:
        # Midscene 报告默认写在 process.cwd()/midscene_run，故将 cwd 设为本次任务目录
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            env=env,
            capture_output=True,
            timeout=run_timeout,
            text=True,
        )
    except subprocess.TimeoutExpired:
        logger.exception("midscene run %s timeout", run_id)
        run = db.get(MidsceneRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = f"执行超时（>{run_timeout}s）；可在服务端环境变量 MIDSCENE_RUN_TIMEOUT_SECONDS 调整"
            run.finished_at = _utcnow()
            db.commit()
        return
    except Exception as e:
        logger.exception("midscene run %s spawn failed: %s", run_id, e)
        run = db.get(MidsceneRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = _utcnow()
            db.commit()
        return

    if proc.stdout:
        logger.warning("midscene stdout (tail): %s", proc.stdout[-8000:])
    if proc.stderr:
        logger.warning("midscene stderr (tail): %s", proc.stderr[-8000:])

    result = _read_result_json(work_dir)
    if result is None:
        # 常见：Node 在加载阶段崩溃、未执行到 run.ts 的 writeResult
        hint = (
            f"未生成 result.json，进程退出码 {proc.returncode}。"
            "请检查：1) backend/midscene-runner 已 npm install；2) 已 npx playwright install chromium；"
            "3) 后端日志中的 Node stderr。"
        )
        tail_out = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        if tail_out:
            hint = f"{hint}\n--- Node 输出（节选）---\n{tail_out[-6000:]}"
        result = {"ok": False, "error": hint, "report_file": None, "video_file": None}

    ok = bool(result.get("ok")) and proc.returncode == 0

    run = db.get(MidsceneRun, run_id)
    if not run:
        return

    run.finished_at = _utcnow()
    if ok:
        run.status = "success"
        run.report_file = result.get("report_file")
        run.video_file = result.get("video_file")
        run.error_message = None
    else:
        run.status = "failed"
        err = result.get("error") or proc.stderr or proc.stdout or f"exit {proc.returncode}"
        run.error_message = str(err)[:8000]
    db.commit()


def run_playwright_sync(
    *,
    db: Session,
    run_id: str,
    payload: MidsceneRunCreate,
) -> None:
    """纯 Playwright：无 API Key、无 Midscene。"""
    settings = get_settings()
    work_dir = (settings.MIDSCENE_ARTIFACTS_DIR / run_id).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    run = db.get(MidsceneRun, run_id)
    if not run:
        logger.error("playwright run %s missing", run_id)
        return

    run.status = "running"
    run.started_at = _utcnow()
    db.commit()

    env = os.environ.copy()
    env["PLAYWRIGHT_WORK_DIR"] = str(work_dir)
    steps = payload.execution_steps or []
    cfg: dict = {
        "startUrl": payload.start_url,
        "headless": payload.headless,
        "recordVideo": payload.record_video,
        "stepGapMs": payload.step_gap_ms,
        "stableWaitAfterStep": payload.stable_wait_after_step,
        "executionSteps": steps,
    }
    if payload.slow_mo_ms is not None and payload.slow_mo_ms > 0:
        cfg["slowMoMs"] = payload.slow_mo_ms
    env["PLAYWRIGHT_RUN_CONFIG_JSON"] = json.dumps(cfg, ensure_ascii=False)

    cmd, _runner_root = _playwright_runner_cmd()
    run_timeout = max(60, int(settings.MIDSCENE_RUN_TIMEOUT_SECONDS))
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            env=env,
            capture_output=True,
            timeout=run_timeout,
            text=True,
        )
    except subprocess.TimeoutExpired:
        logger.exception("playwright run %s timeout", run_id)
        run = db.get(MidsceneRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = f"执行超时（>{run_timeout}s）；可在服务端环境变量 MIDSCENE_RUN_TIMEOUT_SECONDS 调整"
            run.finished_at = _utcnow()
            db.commit()
        return
    except Exception as e:
        logger.exception("playwright run %s spawn failed: %s", run_id, e)
        run = db.get(MidsceneRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = _utcnow()
            db.commit()
        return

    if proc.stdout:
        logger.warning("playwright stdout (tail): %s", proc.stdout[-8000:])
    if proc.stderr:
        logger.warning("playwright stderr (tail): %s", proc.stderr[-8000:])

    result = _read_result_json(work_dir)
    if result is None:
        hint = (
            f"未生成 result.json，进程退出码 {proc.returncode}。"
            f"请检查：1) backend/playwright-runner 已 npm install；2) 已 npx playwright install chromium；"
            f"3) 后端日志中的 Node stderr。"
        )
        tail_out = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        if tail_out:
            hint = f"{hint}\n--- Node 输出（节选）---\n{tail_out[-6000:]}"
        result = {"ok": False, "error": hint, "report_file": None, "video_file": None}

    ok = bool(result.get("ok")) and proc.returncode == 0

    run = db.get(MidsceneRun, run_id)
    if not run:
        return

    run.finished_at = _utcnow()
    if ok:
        run.status = "success"
        run.report_file = result.get("report_file")
        run.video_file = result.get("video_file")
        run.error_message = None
    else:
        run.status = "failed"
        err = result.get("error") or proc.stderr or proc.stdout or f"exit {proc.returncode}"
        run.error_message = str(err)[:8000]
    db.commit()


def create_run_record(
    db: Session,
    *,
    user_id: int,
    payload: MidsceneRunCreate,
) -> MidsceneRun:
    run_id = str(uuid.uuid4())
    instr = (payload.instructions or "").strip()
    if payload.execution_steps and len(payload.execution_steps) > 0:
        instr = instr or f"[步骤编排] {len(payload.execution_steps)} 步"
    if payload.runner == "playwright":
        if payload.execution_steps and len(payload.execution_steps) > 0:
            # 落库完整步骤 JSON，便于前端「运行详情」展示（占位文案 [Playwright] 无信息量）
            instr = json.dumps(payload.execution_steps, ensure_ascii=False, indent=2)
        else:
            instr = instr or "[Playwright]"
    model_name = payload.model.name
    model_family = payload.model.family
    model_base_url = payload.model.base_url.rstrip("/")
    if payload.runner == "playwright":
        model_name = "playwright"
        model_family = "n/a"
        model_base_url = "-"
    run = MidsceneRun(
        id=run_id,
        user_id=user_id,
        status="pending",
        model_name=model_name,
        model_family=model_family,
        model_base_url=model_base_url,
        start_url=payload.start_url,
        instructions=instr,
        instruction_mode=payload.instruction_mode if payload.instruction_mode in (
            "multi_line",
            "single_block",
        ) else "multi_line",
        headless=payload.headless,
        record_video=payload.record_video,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def to_out(run: MidsceneRun) -> MidsceneRunOut:
    return MidsceneRunOut.model_validate(run)


def list_runs(
    db: Session,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[MidsceneRunOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    base = db.query(MidsceneRun).filter(MidsceneRun.user_id == user_id)
    total = base.count()
    offset = (page - 1) * page_size
    rows = (
        base.order_by(MidsceneRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [to_out(r) for r in rows], total


def get_run(db: Session, *, user_id: int, run_id: str) -> MidsceneRun | None:
    if not run_id or len(run_id) != 36:
        return None
    r = db.get(MidsceneRun, run_id)
    if not r or r.user_id != user_id:
        return None
    return r


def artifact_path(user_id: int, run_id: str, kind: str, db: Session) -> Path | None:
    if kind not in {"report", "video"}:
        return None
    run = get_run(db, user_id=user_id, run_id=run_id)
    if not run:
        return None
    rel = run.report_file if kind == "report" else run.video_file
    if not rel:
        return None
    p = _safe_join(run_id, rel)
    if p and p.is_file():
        return p
    return None


def runner_health() -> dict:
    settings = get_settings()
    runner = settings.MIDSCENE_RUNNER_DIR
    tsx = runner / "node_modules" / "tsx" / "dist" / "cli.mjs"
    script = runner / "src" / "run.ts"
    node = shutil.which("node")
    mid_ok = bool(node and tsx.is_file() and script.is_file() and runner.is_dir())
    msg = (
        "Midscene 就绪"
        if mid_ok
        else "请安装 Node.js，并在 backend/midscene-runner 目录执行 npm install 与 npx playwright install chromium"
    )

    pw_dir = settings.PLAYWRIGHT_RUNNER_DIR
    pw_tsx = pw_dir / "node_modules" / "tsx" / "dist" / "cli.mjs"
    pw_script = pw_dir / "src" / "run.ts"
    pw_ok = bool(node and pw_tsx.is_file() and pw_script.is_file() and pw_dir.is_dir())
    pw_msg = (
        "纯 Playwright 就绪"
        if pw_ok
        else "请在 backend/playwright-runner 目录执行 npm install 与 npx playwright install chromium"
    )

    any_ok = mid_ok or pw_ok
    combined = []
    if not node:
        combined.append("未找到 node")
    if mid_ok:
        combined.append("Midscene 可用")
    else:
        combined.append("Midscene 未就绪")
    if pw_ok:
        combined.append("Playwright 可用")
    else:
        combined.append("Playwright 未就绪")

    return {
        "ok": any_ok,
        "node_found": bool(node),
        "runner_dir_exists": runner.is_dir(),
        "tsx_exists": tsx.is_file(),
        "runner_script_exists": script.is_file(),
        "message": "；".join(combined) if combined else msg,
        "playwright_runner_dir_exists": pw_dir.is_dir(),
        "playwright_script_exists": pw_script.is_file(),
        "playwright_ok": pw_ok,
        "playwright_message": pw_msg,
    }
