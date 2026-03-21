from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from dotenv import load_dotenv
import os


Language = Literal["zh", "en"]


@dataclass(frozen=True)
class AppConfig:
    """
    应用运行所需的配置集合，从 .env / 环境变量中加载。
    """
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    language: Language = "zh"
    deepseek_timeout: int = 120
    deepseek_max_tokens: int = 16384
    # LLM 调用在公网/代理下偶发断连，可加大重试次数
    deepseek_llm_retries: int = 6
    # 为 True 时 httpx 不复用长连接（Connection: close），可缓解 incomplete chunked read
    deepseek_http_no_keepalive: bool = False


def _normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    # 兼容用户填写 https://api.deepseek.com/v1
    if base_url.endswith("/v1"):
        base_url = base_url[: -len("/v1")]
    return base_url


def load_config(override_language: Optional[str] = None) -> AppConfig:
    """
    从环境变量加载配置。

    必填：
    - DEEPSEEK_API_KEY
    可选：
    - DEEPSEEK_BASE_URL（默认 https://api.deepseek.com）
    - DEEPSEEK_MODEL（默认 deepseek-chat）
    - DEEPSEEK_TIMEOUT（默认 120，秒）
    - DEEPSEEK_MAX_TOKENS（默认 16384）
    - DEEPSEEK_LLM_RETRIES（默认 6，单次 LLM 调用失败时的最大尝试次数）
    - DEEPSEEK_HTTP_NO_KEEPALIVE（默认 0；设为 1 时禁用 HTTP 连接复用，可缓解断流/chunked 错误）
    - APP_LANGUAGE（默认 zh）
    """
    # 与 backend 集成时，case_gen_service 会先加载 backend/testcase/.env；
    # 此处禁止 override，避免 backend/.env 里空值覆盖已注入的 DEEPSEEK_API_KEY。
    load_dotenv(override=False)

    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("缺少环境变量 DEEPSEEK_API_KEY：请在 .env 中配置你的 API Key")

    base_url = _normalize_base_url(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"

    language_raw = (override_language or os.getenv("APP_LANGUAGE", "zh")).strip().lower()
    language: Language = "zh" if language_raw not in ("en", "zh") else language_raw  # type: ignore[assignment]

    timeout_raw = os.getenv("DEEPSEEK_TIMEOUT", "120").strip()
    max_tokens_raw = os.getenv("DEEPSEEK_MAX_TOKENS", "16384").strip()
    try:
        deepseek_timeout = int(timeout_raw)
    except ValueError:
        deepseek_timeout = 120
    try:
        deepseek_max_tokens = int(max_tokens_raw)
    except ValueError:
        deepseek_max_tokens = 16384

    retries_raw = os.getenv("DEEPSEEK_LLM_RETRIES", "6").strip()
    try:
        deepseek_llm_retries = max(1, int(retries_raw))
    except ValueError:
        deepseek_llm_retries = 6

    no_keep_raw = (os.getenv("DEEPSEEK_HTTP_NO_KEEPALIVE", "0").strip().lower())
    deepseek_http_no_keepalive = no_keep_raw in ("1", "true", "yes", "on")

    return AppConfig(
        deepseek_api_key=api_key,
        deepseek_base_url=base_url,
        deepseek_model=model,
        language=language,
        deepseek_timeout=deepseek_timeout,
        deepseek_max_tokens=deepseek_max_tokens,
        deepseek_llm_retries=deepseek_llm_retries,
        deepseek_http_no_keepalive=deepseek_http_no_keepalive,
    )

