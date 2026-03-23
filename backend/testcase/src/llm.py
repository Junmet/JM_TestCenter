from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
import logging

import httpx
from langchain_openai import ChatOpenAI
from openai import DefaultHttpxClient
from pydantic import TypeAdapter, BaseModel, Field

from .config import AppConfig
from .models import GenerationResult, TestCase
from .prompts import (
    SYSTEM_EN,
    SYSTEM_ZH,
    USER_TEMPLATE,
    OUTLINE_USER_TEMPLATE,
    CASES_BATCH_USER_TEMPLATE,
)


logger = logging.getLogger(__name__)


def _iter_exception_chain(exc: BaseException) -> list[BaseException]:
    """
    遍历整条异常链（含 __cause__ 与 __context__），避免只走 __cause__ 时漏判。
    """
    seen: set[int] = set()
    out: list[BaseException] = []
    stack: list[BaseException] = [exc]
    while stack:
        cur = stack.pop()
        cid = id(cur)
        if cid in seen:
            continue
        seen.add(cid)
        out.append(cur)
        if cur.__cause__ is not None:
            stack.append(cur.__cause__)
        if cur.__context__ is not None and cur.__context__ is not cur.__cause__:
            stack.append(cur.__context__)
    return out


def _is_retryable_llm_transport_error(exc: BaseException) -> bool:
    """
    识别「对端断流 / 网络抖动」等可重试错误（如 incomplete chunked read → APIConnectionError）。
    """
    for cur in _iter_exception_chain(exc):
        name = type(cur).__name__
        if name in (
            "APIConnectionError",
            "APITimeoutError",
            "RemoteProtocolError",
            "ConnectError",
            "ReadTimeout",
            "WriteTimeout",
            "TimeoutException",
        ):
            return True
        s = str(cur).lower()
        if "connection error" in s or "incomplete chunked" in s or "peer closed connection" in s:
            return True
    return False


def _invoke_with_retry(
    llm: ChatOpenAI,
    messages: list[dict[str, str]],
    *,
    step_name: str,
    max_attempts: int = 6,
) -> Any:
    """
    LLM 调用在公网/代理环境下偶发「连接被提前关闭」，对同一请求做有限次退避重试。
    """
    delay = 1.5
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return llm.invoke(messages)
        except Exception as e:
            last = e
            retryable = _is_retryable_llm_transport_error(e)
            if attempt < max_attempts - 1 and retryable:
                logger.warning(
                    "LLM 步骤「%s」失败（第 %d/%d 次），%.1fs 后重试: %s",
                    step_name,
                    attempt + 1,
                    max_attempts,
                    delay,
                    e,
                )
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            if attempt == max_attempts - 1 and retryable:
                logger.error(
                    "LLM 步骤「%s」在 %d 次尝试后仍失败（可重试类网络错误）: %s",
                    step_name,
                    max_attempts,
                    e,
                )
            raise
    assert last is not None
    raise last


def _ensure_langchain_compat() -> None:
    """
    兼容部分 langchain 版本差异：
    某些版本缺少全局属性 verbose/debug，会导致 langchain_core 初始化报错。
    """
    try:
        import langchain  # type: ignore

        if not hasattr(langchain, "verbose"):
            setattr(langchain, "verbose", False)
        if not hasattr(langchain, "debug"):
            setattr(langchain, "debug", False)
        if not hasattr(langchain, "llm_cache"):
            setattr(langchain, "llm_cache", None)
    except Exception:
        # 兼容补丁失败时不阻断主流程，交给后续初始化抛真实异常
        pass


class OutlineResult(BaseModel):
    """
    大纲阶段的 LLM 输出：
    - 上下文摘要（context_summary）用于后续多批用例复用，减少重复提示；
    - mindmap_mermaid / test_points / assumptions / risks / out_of_scope 等用于直接写结果。
    """

    source_name: str
    language: str
    context_summary: str = ""
    mindmap_mermaid: str
    test_points: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


class CasesBatchResult(BaseModel):
    """
    单次“批量生成用例”调用的输出，只关心 test_cases 列表。
    """

    test_cases: list[TestCase] = Field(default_factory=list)


def _optional_http_client(cfg: AppConfig) -> DefaultHttpxClient | None:
    """可选：不复用 HTTP 连接，缓解代理/网关下 incomplete chunked read。"""
    if not cfg.deepseek_http_no_keepalive:
        return None
    return DefaultHttpxClient(
        timeout=httpx.Timeout(cfg.deepseek_timeout),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=0),
        headers={"Connection": "close"},
    )


def build_llm(cfg: AppConfig) -> ChatOpenAI:
    """
    使用 DeepSeek 的 OpenAI 兼容接口初始化 LangChain Chat 模型。

    用例生成专用：强制 JSON 对象输出，降低解析失败概率。
    """
    logger.info(
        "正在初始化 LLM 客户端：base_url=%s，模型=%s，超时=%s，最大 token=%s，LLM 重试=%s，禁用长连接=%s",
        cfg.deepseek_base_url,
        cfg.deepseek_model,
        cfg.deepseek_timeout,
        cfg.deepseek_max_tokens,
        cfg.deepseek_llm_retries,
        cfg.deepseek_http_no_keepalive,
    )
    _ensure_langchain_compat()
    http_client = _optional_http_client(cfg)
    if cfg.deepseek_http_no_keepalive:
        logger.info("已启用 DEEPSEEK_HTTP_NO_KEEPALIVE：不复用长连接（Connection: close）")

    chat_kwargs: dict[str, Any] = {
        "api_key": cfg.deepseek_api_key,
        "base_url": f"{cfg.deepseek_base_url}/v1",
        "model": cfg.deepseek_model,
        "temperature": 0.2,
        "timeout": cfg.deepseek_timeout,
        "max_tokens": cfg.deepseek_max_tokens,
        "max_retries": 5,
        "model_kwargs": {"response_format": {"type": "json_object"}},
    }
    if http_client is not None:
        chat_kwargs["http_client"] = http_client
    return ChatOpenAI(**chat_kwargs)


def build_chat_llm(
    cfg: AppConfig,
    *,
    temperature: float = 0.7,
    model: str | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """
    多轮对话专用：不强制 JSON 模式，避免聊天内容被 response_format 约束。

    与 build_llm 共用同一套 DeepSeek 连接参数（base_url / key / 超时 / 可选禁用长连接）。
    """
    _ensure_langchain_compat()
    http_client = _optional_http_client(cfg)
    m = (model or cfg.deepseek_model).strip() or cfg.deepseek_model
    mt = cfg.deepseek_max_tokens if max_tokens is None else max_tokens
    logger.info(
        "正在初始化对话 LLM：base_url=%s，模型=%s，temperature=%s，max_tokens=%s",
        cfg.deepseek_base_url,
        m,
        temperature,
        mt,
    )
    chat_kwargs: dict[str, Any] = {
        "api_key": cfg.deepseek_api_key,
        "base_url": f"{cfg.deepseek_base_url}/v1",
        "model": m,
        "temperature": temperature,
        "timeout": cfg.deepseek_timeout,
        "max_tokens": mt,
        "max_retries": 5,
    }
    if http_client is not None:
        chat_kwargs["http_client"] = http_client
    return ChatOpenAI(**chat_kwargs)


def chat_completion(
    *,
    cfg: AppConfig,
    llm: ChatOpenAI,
    messages: list[dict[str, str]],
    step_name: str = "ai-chat",
) -> str:
    """
    通用对话补全：messages 为 OpenAI 风格的 role/content 列表（system / user / assistant）。
    """
    msg = _invoke_with_retry(
        llm,
        messages,
        step_name=step_name,
        max_attempts=cfg.deepseek_llm_retries,
    )
    return (getattr(msg, "content", None) or "").strip()


def _lc_messages_from_openai_dicts(messages: list[dict[str, str]]):
    """OpenAI 风格 dict 转为 LangChain BaseMessage 列表，供 stream 使用。"""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    out = []
    for m in messages:
        r, c = m["role"], m["content"]
        if r == "system":
            out.append(SystemMessage(content=c))
        elif r == "user":
            out.append(HumanMessage(content=c))
        elif r == "assistant":
            out.append(AIMessage(content=c))
        else:
            raise ValueError(f"unsupported role: {r}")
    return out


def _chunk_text_content(chunk: Any) -> str:
    """兼容不同 LangChain / 模型返回的 content 形态（str 或 list）。"""
    piece = getattr(chunk, "content", None)
    if piece is None:
        return ""
    if isinstance(piece, str):
        return piece
    if isinstance(piece, list):
        parts: list[str] = []
        for x in piece:
            if isinstance(x, dict) and isinstance(x.get("text"), str):
                parts.append(x["text"])
            elif isinstance(x, str):
                parts.append(x)
        return "".join(parts)
    return str(piece)


def stream_chat_completion_chunks(*, llm: ChatOpenAI, messages: list[dict[str, str]]):
    """
    流式对话：按片段产出文本（DeepSeek OpenAI 兼容流式）。
    不做重试；调用方在失败时可回滚数据库事务。
    """
    lc = _lc_messages_from_openai_dicts(messages)
    for chunk in llm.stream(lc):
        piece = _chunk_text_content(chunk)
        if piece:
            yield piece


def generate_from_text(
    *,
    cfg: AppConfig,
    llm: ChatOpenAI,
    source_name: str,
    document_text: str,
    max_cases: int,
) -> GenerationResult:
    """
    旧版“一次性生成测试点 + 全部用例”的接口，目前保留以兼容/复用。

    由于容易触发 token/长度限制，新流程改为：
    - generate_outline：先拿摘要 + 测试点 + 思维导图；
    - generate_cases_batch：再按测试点分批补齐大量用例。
    """
    system = SYSTEM_ZH if cfg.language == "zh" else SYSTEM_EN

    schema = _generation_schema_json()
    user = USER_TEMPLATE.format(
        source_name=source_name,
        language=cfg.language,
        max_cases=max_cases,
        document_text=document_text,
        schema=schema,
    )

    logger.info(
        "正在调用 LLM 进行完整生成：来源=%s，最大用例数=%d，语言=%s",
        source_name,
        max_cases,
        cfg.language,
    )
    # 使用 messages API，避免 prompt 注入造成格式跑偏
    msg = _invoke_with_retry(
        llm,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        step_name="完整生成",
        max_attempts=cfg.deepseek_llm_retries,
    )

    raw = (msg.content or "").strip()
    data = _parse_or_debug(raw, debug_stem=f"full_{Path(source_name).stem}")
    
    # pydantic 强校验，失败会直接抛出异常，便于定位
    adapter = TypeAdapter(GenerationResult)
    result = adapter.validate_python(data)
    logger.info(
        "完整生成完成：来源=%s，用例数量=%d，测试点数量=%d",
        source_name,
        len(result.test_cases),
        len(result.test_points),
    )
    return result


def generate_outline(
    *,
    cfg: AppConfig,
    llm: ChatOpenAI,
    source_name: str,
    document_text: str,
) -> OutlineResult:
    """
    第 1 阶段：基于原始需求文档生成“测试大纲”：
    - context_summary 摘要：后续所有批次共用，减少重复 prompt；
    - mindmap_mermaid：最终写入思维导图文件；
    - test_points + assumptions/risks/out_of_scope：用于 meta 信息和后续用例扩展。
    """
    system = SYSTEM_ZH if cfg.language == "zh" else SYSTEM_EN
    schema = _outline_schema_json()
    user = OUTLINE_USER_TEMPLATE.format(
        source_name=source_name,
        language=cfg.language,
        document_text=document_text,
        schema=schema,
    )
    logger.info("正在生成大纲：来源=%s，语言=%s", source_name, cfg.language)
    msg = _invoke_with_retry(
        llm,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        step_name="生成大纲",
        max_attempts=cfg.deepseek_llm_retries,
    )
    raw = (msg.content or "").strip()
    data = _parse_or_debug(raw, debug_stem=f"outline_{Path(source_name).stem}")
    outline = TypeAdapter(OutlineResult).validate_python(data)
    logger.info(
        "大纲生成完成：来源=%s，测试点数量=%d",
        source_name,
        len(outline.test_points),
    )
    return outline


def generate_cases_batch(
    *,
    cfg: AppConfig,
    llm: ChatOpenAI,
    source_name: str,
    context_summary: str,
    test_point: str,
    batch_size: int,
    existing_titles: list[str],
) -> CasesBatchResult:
    """
    第 2 阶段：围绕单个测试点，批量生成若干条测试用例。

    - context_summary：来自第 1 阶段的大纲摘要；
    - test_point：当前要展开的测试点；
    - batch_size：本批次期望的用例条数；
    - existing_titles：用于避免生成重复标题（仅传入末尾若干条以控制 prompt 长度）。
    """
    system = SYSTEM_ZH if cfg.language == "zh" else SYSTEM_EN
    schema = _cases_batch_schema_json()
    existing_titles_str = "\n".join([f"- {t}" for t in existing_titles[-120:]]) if existing_titles else "（无）"
    user = CASES_BATCH_USER_TEMPLATE.format(
        source_name=source_name,
        language=cfg.language,
        context_summary=context_summary,
        test_point=test_point,
        batch_size=batch_size,
        existing_titles=existing_titles_str,
        schema=schema,
    )

    # 批量生成时模型偶尔返回不合法 JSON（缺逗号等），解析失败时自动重试最多 2 次
    last_error: Exception | None = None
    for attempt in range(3):
        logger.info(
            "正在生成用例批次（第 %d/3 次）：来源=%s，测试点=%.30s，每批大小=%d，已有标题数=%d",
            attempt + 1,
            source_name,
            test_point,
            batch_size,
            len(existing_titles),
        )
        msg = _invoke_with_retry(
            llm,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            step_name=f"用例批次(第{attempt + 1}次)",
            max_attempts=cfg.deepseek_llm_retries,
        )
        raw = (msg.content or "").strip()
        try:
            data = _parse_or_debug(raw, debug_stem=f"cases_{Path(source_name).stem}")
            result = TypeAdapter(CasesBatchResult).validate_python(data)
            logger.info(
                "用例批次生成完成：来源=%s，测试点=%.30s，本批生成=%d",
                source_name,
                test_point,
                len(result.test_cases),
            )
            return result
        except RuntimeError as e:
            last_error = e
            logger.warning(
                "第 %d/3 次批量用例 JSON 解析失败（来源=%s，测试点=%.30s）：%s",
                attempt + 1,
                source_name,
                test_point,
                e,
            )
            if attempt < 2:
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("批量用例 JSON 解析失败（已重试多次仍失败）。")


def _parse_or_debug(raw: str, *, debug_stem: str) -> Any:
    """
    统一的 JSON 解析入口：
    - 优先尝试用 _safe_json_loads 提取 JSON；
    - 如失败，把原始内容写入 debug/ 目录，方便排查且不影响 output；
    - 抛出 RuntimeError 给上层，避免静默失败。
    """
    try:
        return _safe_json_loads(raw)
    except Exception as e:  # noqa: BLE001
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / f"debug_{debug_stem}_{ts}.txt"
        debug_path.write_text(raw or "<空响应>", encoding="utf-8")
        logger.error(
            "模型返回 JSON 解析失败，已将原始内容保存到 %s：%s",
            debug_path,
            e,
        )
        raise RuntimeError(
            f"模型返回 JSON 解析失败。原始内容已保存到 {debug_path}。"
        ) from e


def _repair_json(json_str: str) -> str:
    """
    尝试修复模型返回中常见的 JSON 语法错误：尾逗号、相邻对象间缺逗号。
    """
    # 尾逗号：, ] 或 , } 改为 ] / }
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = re.sub(r",\s*}", "}", json_str)
    # 数组/对象之间缺逗号：} 后面紧跟 { 时补逗号
    json_str = re.sub(r"}\s*{", "}, {", json_str)
    return json_str


def _safe_json_loads(s: str) -> Any:
    """
    尝试从模型返回内容中提取 JSON：
    - 去除 BOM 和首尾空白
    - 自动从包含 ```json ... ``` 或解释性文字的长文本中“截取”第一个完整的 JSON 对象
    - 解析失败时尝试简单修复（尾逗号、缺逗号）后再解析
    """
    if not s:
        raise ValueError("模型返回为空响应。")

    # 去掉 BOM / 首尾空白
    s = s.strip("\ufeff \t\r\n")

    # 若整体是 markdown 代码块，先粗略剥离 ``` 包裹及 json 语言标签
    if s.startswith("```"):
        # 删除首尾成对的 ```
        s = s.strip("`")
        # 删除第一行可能的语言标识
        if "\n" in s:
            first_line, rest = s.split("\n", 1)
            if first_line.lower().startswith("json"):
                s = rest
            else:
                s = first_line + "\n" + rest

    s = s.strip()

    # 确定待解析的 JSON 片段
    if s.startswith("{") and s.endswith("}"):
        json_str = s
    else:
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("模型返回中未找到 JSON 对象。")
        json_str = s[start : end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    # 尝试修复常见语法错误后再解析
    repaired = _repair_json(json_str)
    return json.loads(repaired)


def _generation_schema_json() -> str:
    """
    给模型一份“目标结构”的强提示，显著提升结构化输出稳定性。
    """
    schema_obj: dict[str, Any] = {
        "type": "object",
        "required": [
            "source_name",
            "language",
            "mindmap_mermaid",
            "test_points",
            "test_cases",
            "assumptions",
            "risks",
            "out_of_scope",
        ],
        "properties": {
            "source_name": {"type": "string"},
            "language": {"type": "string"},
            "mindmap_mermaid": {"type": "string", "description": "Mermaid mindmap content only. First line must be mindmap."},
            "test_points": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "out_of_scope": {"type": "array", "items": {"type": "string"}},
            "test_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "priority",
                        "module",
                        "title",
                        "summary",
                        "preconditions",
                        "steps",
                        "expected",
                        "actual_result",
                        "test_type",
                        "data",
                        "remarks",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "priority": {"type": "string"},
                        "module": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string", "description": "摘要，一句话概括本用例验证点"},
                        "preconditions": {"type": "string"},
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "expected": {"type": "array", "items": {"type": "string"}},
                        "actual_result": {"type": "string", "description": "实际结果，执行后填写，生成时可为空字符串"},
                        "test_type": {"type": "string"},
                        "data": {"type": "string"},
                        "remarks": {"type": "string"},
                    },
                },
            },
        },
    }
    return json.dumps(schema_obj, ensure_ascii=False, indent=2)


def _outline_schema_json() -> str:
    schema_obj: dict[str, Any] = {
        "type": "object",
        "required": [
            "source_name",
            "language",
            "context_summary",
            "mindmap_mermaid",
            "test_points",
            "assumptions",
            "risks",
            "out_of_scope",
        ],
        "properties": {
            "source_name": {"type": "string"},
            "language": {"type": "string"},
            "context_summary": {"type": "string"},
            "mindmap_mermaid": {"type": "string"},
            "test_points": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "out_of_scope": {"type": "array", "items": {"type": "string"}},
        },
    }
    return json.dumps(schema_obj, ensure_ascii=False, indent=2)


def _cases_batch_schema_json() -> str:
    schema_obj: dict[str, Any] = {
        "type": "object",
        "required": ["test_cases"],
        "properties": {
            "test_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "priority",
                        "module",
                        "title",
                        "summary",
                        "preconditions",
                        "steps",
                        "expected",
                        "actual_result",
                        "test_type",
                        "data",
                        "remarks",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "priority": {"type": "string"},
                        "module": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string", "description": "摘要，一句话概括本用例验证点"},
                        "preconditions": {"type": "string"},
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "expected": {"type": "array", "items": {"type": "string"}},
                        "actual_result": {"type": "string", "description": "实际结果，执行后填写，生成时可为空字符串"},
                        "test_type": {"type": "string"},
                        "data": {"type": "string"},
                        "remarks": {"type": "string"},
                    },
                },
            }
        },
    }
    return json.dumps(schema_obj, ensure_ascii=False, indent=2)

