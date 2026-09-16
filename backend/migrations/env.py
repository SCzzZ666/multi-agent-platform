"""Alembic 迁移环境（保持独立：不 import 业务包，迁移用 op.execute 手写 SQL）。

数据库 URL 优先读环境变量 MIGRATION_DATABASE_URL（见项目根 .env），
缺省回退本地开发超管连接。迁移/user 分离在后续迁移步中按 04 物理设计落地。
"""
from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

config.set_main_option(
    "sqlalchemy.url",
    os.environ.get(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://ai_native:ai_native_dev@localhost:5432/ai_native",
    ),
)

# 不绑定 ORM metadata：迁移是 04 物理设计的有序 SQL，非模型映射。
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()