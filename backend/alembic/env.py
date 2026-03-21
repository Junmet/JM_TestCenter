from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic 在启动时需要把项目根路径加入 sys.path
from app.core.config import get_settings
from app.db.base import Base

import app.db.models  # noqa: F401  # 确保模型被 import，从而注册到 Base.metadata

config = context.config

# Alembic 默认会读取 alembic.ini 的 logging 配置。
# 由于本项目的 alembic.ini 由模板简化过，这里对缺失段做兼容处理，
# 以保证迁移逻辑优先可运行。
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = Base.metadata


def get_database_url() -> str:
    # 允许你在执行 alembic 时不显式传参数，直接用 .env
    settings = get_settings()
    return settings.mysql_url


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

