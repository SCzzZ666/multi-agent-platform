"""最小配置装载（生产必须拒绝测试身份/宽松配置，见 10 基线 §13）。

背景：真实凭据只放项目根的 `.env`（被 .gitignore 排除），正文只经 credential_ref 进入应用。
此模块用标准库解析 `.env`，不引入额外依赖；`setdefault` 保证显式环境变量优先于文件。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# backend/src/ai_native/bootstrap/config.py -> parents[4] = project/
_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class Settings:
    env: str
    profile: str
    dashscope_api_key: str | None
    dashscope_base_url: str
    deepseek_api_key: str | None
    deepseek_base_url: str
    kimi_api_key: str | None
    kimi_base_url: str
    database_url: str
    migration_database_url: str
    worker_database_url: str
    artifact_store_dir: str

    @classmethod
    def load(cls, env_path: Path | None = None) -> "Settings":
        _load_env(env_path or _ENV_PATH)
        return cls(
            env=os.getenv("AI_NATIVE_ENV", "development"),
            profile=os.getenv("APP_PROFILE", "development"),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            dashscope_base_url=os.getenv(
                "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            kimi_api_key=os.getenv("KIMI_API_KEY"),
            kimi_base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            database_url=os.getenv(
                "DATABASE_URL", "postgresql+psycopg://api_user:ai_native_dev@localhost:5432/ai_native"
            ),
            migration_database_url=os.getenv(
                "MIGRATION_DATABASE_URL",
                "postgresql+psycopg://migrator:ai_native_dev@localhost:5432/ai_native",
            ),
            worker_database_url=os.getenv(
                "WORKER_DATABASE_URL",
                "postgresql+psycopg://worker_user:ai_native_dev@localhost:5432/ai_native",
            ),
            artifact_store_dir=os.getenv("ARTIFACT_STORE_DIR", ".data/artifacts"),
        )