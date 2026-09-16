"""DB 装配：engine / session / 项目作用域上下文（RLS 应用账户）。

约定（04 基线 6.1）：应用账户非 superuser、非表所有者，RLS 作纵深防御；
每个项目作用域事务内必须先 SET LOCAL app.project_id（project_context），
否则 RLS 会过滤掉所有行（policy 用 platform.current_project_id()）。
未做 RLS 的 app_user/project/project_member 用于建立上下文，无需 project_context。
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ai_native.bootstrap.config import Settings

_settings = Settings.load()


class Base(DeclarativeBase):
    pass


engine = create_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def project_context(db: Session, project_id) -> None:
    """在事务内设置 RLS 项目上下文（同事务内生效）。

    SET 是数据库工具命令、不支持参数绑定，故直接内联 uuid（uuid 值安全、无注入面）。
    """
    db.execute(text(f"SET LOCAL app.project_id = '{project_id}'"))