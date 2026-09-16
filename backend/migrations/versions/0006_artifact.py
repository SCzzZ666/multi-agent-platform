r"""迁移第⑤步（artifact）：artifact 表（run_id 的外键在 run 表创建后于 0007 补）。"""
from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.artifact (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      run_id uuid, artifact_type text NOT NULL, media_type text NOT NULL, object_ref text NOT NULL,
      content_digest platform.sha256_digest NOT NULL, size_bytes bigint NOT NULL CHECK(size_bytes>=0),
      sensitivity text NOT NULL DEFAULT 'INTERNAL' CHECK(sensitivity IN ('PUBLIC','INTERNAL','SENSITIVE')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), deleted_at timestamptz,
      UNIQUE(project_id,id), UNIQUE(project_id,content_digest,artifact_type)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass