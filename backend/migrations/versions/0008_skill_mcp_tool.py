r"""迁移第⑦步：skill / skill_version / mcp_connection / credential_ref / tool_schema_version / capability_binding。"""
from __future__ import annotations

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.skill (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      skill_key text NOT NULL, name text NOT NULL, status text NOT NULL CHECK(status IN ('HIDDEN','ENABLED','SUSPENDED','RETIRED')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(project_id,id), UNIQUE(project_id,skill_key)
    )""",
    """CREATE TABLE platform.skill_version (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, skill_id uuid NOT NULL,
      version_no integer NOT NULL CHECK(version_no>0), package_digest platform.sha256_digest NOT NULL, manifest jsonb NOT NULL,
      validation_status text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,skill_id) REFERENCES platform.skill(project_id,id), UNIQUE(project_id,id), UNIQUE(skill_id,version_no)
    )""",
    """CREATE TABLE platform.mcp_connection (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      connection_key text NOT NULL, transport text NOT NULL, endpoint_identity_digest platform.sha256_digest NOT NULL,
      credential_ref_id uuid, status text NOT NULL CHECK(status IN ('HIDDEN','ENABLED','DRIFTED','SUSPENDED','RETIRED')),
      policy jsonb NOT NULL, row_version bigint NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(project_id,id), UNIQUE(project_id,connection_key)
    )""",
    """CREATE TABLE platform.credential_ref (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      provider text NOT NULL, secret_ref text NOT NULL, allowed_purpose text NOT NULL, status text NOT NULL CHECK(status IN ('ACTIVE','REVOKED','EXPIRED')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), expires_at timestamptz, revoked_at timestamptz,
      UNIQUE(project_id,id), UNIQUE(project_id,secret_ref)
    )""",
    "ALTER TABLE platform.mcp_connection ADD CONSTRAINT mcp_credential_fk FOREIGN KEY(project_id,credential_ref_id) REFERENCES platform.credential_ref(project_id,id)",
    """CREATE TABLE platform.tool_schema_version (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      mcp_connection_id uuid, tool_key text NOT NULL, version_no integer NOT NULL CHECK(version_no>0), schema_json jsonb NOT NULL,
      schema_digest platform.sha256_digest NOT NULL, risk_class text NOT NULL, idempotency_class text NOT NULL,
      status text NOT NULL CHECK(status IN ('DISCOVERED','VALIDATING','ENABLED','DRIFTED','SUSPENDED','RETIRED')),
      discovered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,mcp_connection_id) REFERENCES platform.mcp_connection(project_id,id),
      UNIQUE(project_id,id), UNIQUE(project_id,tool_key,version_no), UNIQUE(project_id,tool_key,schema_digest)
    )""",
    """CREATE TABLE platform.capability_binding (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      workflow_version_id uuid NOT NULL, node_key text NOT NULL, role_id text NOT NULL, capability_kind text NOT NULL,
      tool_schema_version_id uuid, skill_version_id uuid, scope_version text NOT NULL DEFAULT 'scope.v1', resource_scope jsonb NOT NULL,
      data_egress jsonb NOT NULL, risk_ceiling text NOT NULL, schema_digest platform.sha256_digest, status text NOT NULL,
      row_version bigint NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,workflow_version_id) REFERENCES platform.workflow_version(project_id,id),
      FOREIGN KEY(project_id,tool_schema_version_id) REFERENCES platform.tool_schema_version(project_id,id),
      FOREIGN KEY(project_id,skill_version_id) REFERENCES platform.skill_version(project_id,id),
      UNIQUE(project_id,id), UNIQUE(workflow_version_id,node_key,capability_kind,tool_schema_version_id,skill_version_id),
      CHECK(status IN ('ACTIVE','SUSPENDED','REVOKED'))
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass