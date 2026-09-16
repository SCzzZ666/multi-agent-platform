r"""迁移第③步：source / chat_thread / chat_message / proposal。"""
from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.source (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      source_type text NOT NULL, title text NOT NULL, uri text, content_digest platform.sha256_digest,
      artifact_ref text, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, row_version bigint NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), deleted_at timestamptz,
      UNIQUE (project_id,id)
    )""",
    """CREATE TABLE platform.chat_thread (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      title text NOT NULL, row_version bigint NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), archived_at timestamptz,
      UNIQUE (project_id,id)
    )""",
    """CREATE TABLE platform.chat_message (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, thread_id uuid NOT NULL,
      actor_type text NOT NULL CHECK (actor_type IN ('USER','AGENT','SYSTEM')), role_id text,
      body text NOT NULL, citations jsonb NOT NULL DEFAULT '[]'::jsonb, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY (project_id,thread_id) REFERENCES platform.chat_thread(project_id,id), UNIQUE(project_id,id)
    )""",
    """CREATE TABLE platform.proposal (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      proposal_type text NOT NULL, target_id uuid, base_row_version bigint, payload jsonb NOT NULL,
      status text NOT NULL CHECK (status IN ('DRAFT','PENDING','ACCEPTED','REJECTED','CONFLICT')),
      created_by uuid NOT NULL REFERENCES platform.app_user(id), created_at timestamptz NOT NULL DEFAULT clock_timestamp(), decided_at timestamptz,
      UNIQUE(project_id,id)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass