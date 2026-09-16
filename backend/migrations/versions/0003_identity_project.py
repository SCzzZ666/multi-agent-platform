r"""迁移第②步：identity / project（app_user / project / project_member）。"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.app_user (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)),
      subject text NOT NULL UNIQUE, display_name text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), disabled_at timestamptz
    )""",
    """CREATE TABLE platform.project (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)),
      name text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
      status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
      owner_user_id uuid NOT NULL REFERENCES platform.app_user(id),
      row_version bigint NOT NULL DEFAULT 1 CHECK (row_version > 0),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(), archived_at timestamptz,
      UNIQUE (id, owner_user_id)
    )""",
    """CREATE TABLE platform.project_member (
      project_id uuid NOT NULL REFERENCES platform.project(id),
      user_id uuid NOT NULL REFERENCES platform.app_user(id),
      member_role text NOT NULL CHECK (member_role IN ('OWNER','EDITOR','REVIEWER','VIEWER','ADMIN')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), revoked_at timestamptz,
      PRIMARY KEY (project_id,user_id)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass