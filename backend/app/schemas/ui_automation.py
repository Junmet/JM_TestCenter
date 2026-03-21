from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MidsceneModelConfig(BaseModel):
    """与 Midscene v1 的 OpenAI 兼容接口一致；API Key 不落库，仅随本次任务传入子进程。"""

    base_url: str = Field(..., description="OpenAI 兼容 Base URL，如 https://api.openai.com/v1")
    # 允许空串：runner=playwright 时不使用模型；Midscene 任务在下方 model_validator 中再校验
    api_key: str = Field(default="", description="模型 API Key（Midscene 必填）")
    name: str = Field(..., min_length=1, description="模型名称，如 gpt-4o")
    family: str = Field(
        ...,
        min_length=1,
        description="VL 模式，写入 MIDSCENE_VL_MODE（如 qwen3-vl、gemini、doubao-vision、vlm-ui-tars）",
    )


class MidsceneRunCreate(BaseModel):
    """runner=playwright 时不调用模型，须步骤编排且步骤中不可含 aiAction/aiWaitFor。"""

    runner: Literal["midscene", "playwright"] = Field(
        "midscene",
        description="midscene：Midscene+视觉模型；playwright：纯 Playwright，高效、需 locator",
    )
    model: MidsceneModelConfig
    start_url: str = Field(..., min_length=1, description="浏览器首先打开的页面")
    instructions: str = Field(
        default="",
        description="自然语言步骤；与 execution_steps 二选一或同时提供说明文字",
    )
    instruction_mode: str = Field(
        "multi_line",
        description="multi_line：每行一条 aiAct；single_block：整段一条 aiAct（仅未使用 execution_steps 时生效）",
    )
    headless: bool = True
    record_video: bool = False
    step_gap_ms: int = Field(
        400,
        ge=0,
        le=120_000,
        description="每步 aiAction 之后额外等待（毫秒）；与稳定等待叠加。复杂/慢页可调大",
    )
    stable_wait_after_step: bool = Field(
        False,
        description="每步后轻量 domcontentloaded 等待 + 步间间隔；抢步或慢页再勾选。networkidle 见服务端环境变量（见 backend/midscene-runner README）",
    )
    execution_steps: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "可选：步骤编排（JSON 数组）。若非空则优先按此执行，混合 aiAction 与 Playwright 白名单操作。"
            "见 backend/midscene-runner README；纯 Playwright 见 backend/playwright-runner/PIPELINE_SPEC.md。"
        ),
    )
    slow_mo_ms: int | None = Field(
        None,
        ge=0,
        le=2000,
        description="仅 Playwright：注入 slowMo(ms)，操作之间延迟，便于录屏观察；0 或不传表示关闭；最大 2000",
    )

    @model_validator(mode="after")
    def instructions_or_pipeline(self) -> MidsceneRunCreate:
        if self.runner == "midscene" and not (self.model.api_key or "").strip():
            raise ValueError("使用 Midscene 时 API Key 不能为空")
        if self.runner == "playwright":
            steps = self.execution_steps or []
            if len(steps) == 0:
                raise ValueError("纯 Playwright 须使用步骤编排，且 execution_steps 非空")
            for i, s in enumerate(steps):
                if not isinstance(s, dict):
                    raise ValueError(f"execution_steps[{i}] 须为 JSON 对象")
                t = str(s.get("type") or "").strip()
                if t in ("aiAction", "aiWaitFor"):
                    raise ValueError(
                        f"纯 Playwright 不可使用 {t}（第 {i + 1} 步），请改用 click/fill/locator 等确定性步骤"
                    )
            return self
        has_steps = bool(self.execution_steps and len(self.execution_steps) > 0)
        has_text = bool((self.instructions or "").strip())
        if not has_steps and not has_text:
            raise ValueError("instructions 与 execution_steps 至少填写其一")
        return self


class MidsceneRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    error_message: str | None
    model_name: str
    model_family: str
    model_base_url: str
    start_url: str
    instructions: str
    instruction_mode: str
    headless: bool
    record_video: bool
    report_file: str | None
    video_file: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class MidsceneRunListResponse(BaseModel):
    items: list[MidsceneRunOut]
    total: int
    page: int
    page_size: int


class MidsceneRunnerHealth(BaseModel):
    ok: bool
    node_found: bool
    runner_dir_exists: bool
    tsx_exists: bool
    runner_script_exists: bool
    message: str
    playwright_runner_dir_exists: bool = False
    playwright_script_exists: bool = False
    playwright_ok: bool = False
    playwright_message: str = ""
