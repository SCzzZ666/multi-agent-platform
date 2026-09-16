r"""迁移第①步（补）：platform 辅助函数与 sha256_digest 域（04 02_初始迁移设计.sql）。"""
from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_STMTS = [
    "CREATE OR REPLACE FUNCTION platform.is_uuid_v7(value uuid) RETURNS boolean "
    "LANGUAGE sql IMMUTABLE STRICT AS $$ SELECT substring(value::text from 15 for 1) = '7' $$",
    "CREATE OR REPLACE FUNCTION platform.current_project_id() RETURNS uuid "
    "LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.project_id', true), '')::uuid $$",
    "CREATE DOMAIN platform.sha256_digest AS char(71) "
    "CHECK (VALUE ~ '^sha256:[0-9a-f]{64}$')",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    # 不可逆删除不进普通回滚，走前向修复（04 基线 6.3）
    pass