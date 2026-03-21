"""
用例生成失败时：对外仅返回简短文案；详细排查说明只写服务端日志。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 给前端 / HTTP detail 用，不暴露部署路径与 .env 配置项
PUBLIC_GENERATION_FAILED = "用例生成失败，请稍后重试"


def _exception_fingerprint(exc: BaseException) -> str:
    """收集整条异常链上的类型名与文本，用于分类。"""
    parts: list[str] = []
    stack: list[BaseException] = [exc]
    seen: set[int] = set()
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        parts.append(type(cur).__name__)
        parts.append(str(cur))
        if cur.__cause__ is not None:
            stack.append(cur.__cause__)
        ctx = getattr(cur, "__context__", None)
        if ctx is not None and ctx is not cur.__cause__:
            stack.append(ctx)
    return " ".join(parts).lower()


def log_generation_failure_hints(exc: BaseException) -> None:
    """
    将运维向排查说明写入日志，不返回给客户端。
    """
    blob = _exception_fingerprint(exc)

    if _is_llm_transport(blob):
        logger.warning(
            "case-gen LLM 连接异常（仅服务端可见排查建议）："
            "检查网络/代理/VPN；backend/testcase/.env 可设 DEEPSEEK_HTTP_NO_KEEPALIVE=1；"
            "增大 DEEPSEEK_TIMEOUT；启动 uvicorn 时 --reload-dir testcase 或手动重启以加载 testcase 代码。"
        )
        return

    if _is_timeout(blob):
        logger.warning(
            "case-gen 请求超时（仅服务端可见排查建议）："
            "可在 backend/testcase/.env 增大 DEEPSEEK_TIMEOUT；或降低目标用例数。"
        )
        return

    if "缺少环境变量 deepseek_api_key" in blob:
        logger.warning(
            "case-gen 未配置 API Key（仅服务端可见排查建议）：在 backend/testcase/.env 设置 DEEPSEEK_API_KEY 并重启后端。"
        )


def _is_llm_transport(blob: str) -> bool:
    return (
        "incomplete chunked" in blob
        or "peer closed connection" in blob
        or "apiconnectionerror" in blob
        or "connection error" in blob
        or "remoteprotocolerror" in blob
        or "httpx.remoteprotocolerror" in blob
    )


def _is_timeout(blob: str) -> bool:
    return "apptimeouterror" in blob or "readtimeout" in blob or "timeout" in blob
