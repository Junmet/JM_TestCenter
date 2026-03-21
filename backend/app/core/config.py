from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # 先用代码默认值保证迁移/开发可跑通，后续在确认 `.env` 内容正确后再启用 env_file。
    model_config = SettingsConfigDict(extra="ignore")

    # MySQL
    MYSQL_HOST: str = "192.168.138.128"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DB: str = "jmtestcenter"

    # JWT
    # 允许开发环境先跑通（生产请务必替换）
    JWT_ACCESS_SECRET: str = "replace_me_access_secret"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_ALG: str = "HS256"
    JWT_ISSUER: str = "jmtestcenter"

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Midscene.js：Node 运行器目录（默认 backend/midscene-runner）与产物目录
    MIDSCENE_RUNNER_DIR: Path = BACKEND_ROOT / "midscene-runner"
    # 纯 Playwright 运行器（无 LLM，见 backend/playwright-runner/README.md）
    PLAYWRIGHT_RUNNER_DIR: Path = BACKEND_ROOT / "playwright-runner"
    MIDSCENE_ARTIFACTS_DIR: Path = BACKEND_ROOT / "data" / "midscene_runs"
    # 为 True 时向子进程注入 MIDSCENE_SETTLE_NETWORK_IDLE=1（SPA 默认关闭，易卡时可开）
    MIDSCENE_SETTLE_NETWORK_IDLE: bool = False
    # Node midscene-runner 单次任务最长等待（秒），超时后 kill 子进程；默认 3600（与「一小时无结果」一致）
    MIDSCENE_RUN_TIMEOUT_SECONDS: int = 3600
    # 单步 aiAction 最长毫秒数，传给 MIDSCENE_AI_ACTION_TIMEOUT_MS；0 表示不限制单步（仍受上面总超时约束）
    MIDSCENE_AI_ACTION_TIMEOUT_MS: int = 300_000
    # Midscene 内部「重规划」次数上限，传给 MIDSCENE_REPLANNING_CYCLE_LIMIT（略低于库默认 10，避免单步拖太久）
    MIDSCENE_REPLANNING_CYCLE_LIMIT: int = 8

    @property
    def mysql_url(self) -> str:
        # charset=utf8mb4 防止中文/多字符集问题
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

