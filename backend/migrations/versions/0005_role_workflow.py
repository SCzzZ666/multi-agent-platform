r"""迁移第④步：role_catalog_version / role_definition / workflow_template_version / draft / revision / version。"""
from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.role_catalog_version (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), catalog_key text NOT NULL, version_no integer NOT NULL CHECK(version_no>0),
      content_digest platform.sha256_digest NOT NULL, status text NOT NULL CHECK(status IN ('PUBLISHED','RETIRED')),
      published_at timestamptz NOT NULL, UNIQUE(catalog_key,version_no), UNIQUE(content_digest)
    )""",
    """CREATE TABLE platform.role_definition (
      catalog_version_id uuid NOT NULL REFERENCES platform.role_catalog_version(id), role_id text NOT NULL,
      name text NOT NULL, responsibility text NOT NULL, capability_ceiling jsonb NOT NULL,
      profile_json jsonb NOT NULL,
      PRIMARY KEY(catalog_version_id,role_id)
    )""",
    """CREATE TABLE platform.workflow_template_version (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), template_key text NOT NULL,
      version_no integer NOT NULL CHECK(version_no>0), fixed_definition_json jsonb NOT NULL,
      extension_policy_json jsonb NOT NULL, content_digest platform.sha256_digest NOT NULL,
      status text NOT NULL CHECK(status IN ('PUBLISHED','RETIRED')), published_at timestamptz NOT NULL,
      UNIQUE(template_key,version_no), UNIQUE(content_digest)
    )""",
    """CREATE TABLE platform.workflow_draft (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      workflow_key text NOT NULL, title text NOT NULL, template_version_id uuid NOT NULL REFERENCES platform.workflow_template_version(id),
      row_version bigint NOT NULL DEFAULT 1,
      current_revision_no integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(project_id,id), UNIQUE(project_id,workflow_key)
    )""",
    """CREATE TABLE platform.workflow_draft_revision (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, workflow_draft_id uuid NOT NULL,
      revision_no integer NOT NULL CHECK(revision_no>0), definition_json jsonb NOT NULL, content_digest platform.sha256_digest NOT NULL,
      created_by uuid NOT NULL REFERENCES platform.app_user(id), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,workflow_draft_id) REFERENCES platform.workflow_draft(project_id,id),
      UNIQUE(workflow_draft_id,revision_no), UNIQUE(project_id,id)
    )""",
    """CREATE TABLE platform.workflow_version (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, workflow_draft_id uuid NOT NULL,
      version_no integer NOT NULL CHECK(version_no>0), schema_version text NOT NULL,
      role_catalog_version_id uuid NOT NULL REFERENCES platform.role_catalog_version(id),
      template_version_id uuid NOT NULL REFERENCES platform.workflow_template_version(id),
      definition_json jsonb NOT NULL, content_digest platform.sha256_digest NOT NULL,
      published_by uuid NOT NULL REFERENCES platform.app_user(id), published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,workflow_draft_id) REFERENCES platform.workflow_draft(project_id,id),
      UNIQUE(project_id,id), UNIQUE(project_id,workflow_draft_id,version_no), UNIQUE(project_id,content_digest)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass