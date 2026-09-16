r"""迁移第⑨步：workspace_grant / workspace / manifest / manifest_entry / runner_task / patch / patch_apply。"""
from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.workspace_grant (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      directory_id uuid NOT NULL CHECK(platform.is_uuid_v7(directory_id)), host_identity_digest platform.sha256_digest NOT NULL,
      access_mode text NOT NULL CHECK(access_mode IN ('READ_ONLY','READ_WRITE')), status text NOT NULL CHECK(status IN ('ACTIVE','REVOKED','EXPIRED')),
      expires_at timestamptz NOT NULL, baseline_manifest_digest platform.sha256_digest, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), revoked_at timestamptz,
      UNIQUE(project_id,id), UNIQUE(project_id,directory_id)
    )""",
    """CREATE TABLE platform.workspace (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL, grant_id uuid NOT NULL,
      state text NOT NULL, source_manifest_id uuid, copy_manifest_id uuid, managed_location_ref text NOT NULL,
      retain_until timestamptz, quarantined_until timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id), FOREIGN KEY(project_id,grant_id) REFERENCES platform.workspace_grant(project_id,id),
      UNIQUE(project_id,id), CHECK(state IN ('GRANTED','COPYING','READY','EXECUTING','PATCH_GENERATED','RETAINED','QUARANTINED','CLEANED','COPY_FAILED'))
    )""",
    """CREATE TABLE platform.manifest (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id), workspace_id uuid,
      directory_id uuid NOT NULL, manifest_kind text NOT NULL, schema_version text NOT NULL, content_digest platform.sha256_digest NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(project_id,id), UNIQUE(project_id,content_digest,manifest_kind),
      FOREIGN KEY(project_id,workspace_id) REFERENCES platform.workspace(project_id,id)
    )""",
    """CREATE TABLE platform.manifest_entry (
      manifest_id uuid NOT NULL REFERENCES platform.manifest(id), logical_path text NOT NULL,
      entry_type text NOT NULL CHECK(entry_type IN ('FILE','DIRECTORY','EXCLUDED')),
      content_digest platform.sha256_digest, size_bytes bigint CHECK(size_bytes>=0), file_identity_digest platform.sha256_digest,
      excluded_reason text, PRIMARY KEY(manifest_id,logical_path), CHECK(logical_path !~ '(^|[\\/])\.\.([\\/]|$)')
    )""",
    "ALTER TABLE platform.workspace ADD CONSTRAINT workspace_source_manifest_fk FOREIGN KEY(project_id,source_manifest_id) REFERENCES platform.manifest(project_id,id)",
    "ALTER TABLE platform.workspace ADD CONSTRAINT workspace_copy_manifest_fk FOREIGN KEY(project_id,copy_manifest_id) REFERENCES platform.manifest(project_id,id)",
    """CREATE TABLE platform.runner_task (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL, node_attempt_id uuid NOT NULL, workspace_id uuid NOT NULL,
      execution_profile_id text NOT NULL, profile_digest platform.sha256_digest NOT NULL, argv_digest platform.sha256_digest NOT NULL,
      secret_refs jsonb NOT NULL DEFAULT '[]'::jsonb, network_policy jsonb NOT NULL, resource_limits jsonb NOT NULL,
      state text NOT NULL, exit_code integer, started_at timestamptz, ended_at timestamptz,
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id), FOREIGN KEY(project_id,node_attempt_id) REFERENCES platform.node_attempt(project_id,id),
      FOREIGN KEY(project_id,workspace_id) REFERENCES platform.workspace(project_id,id), UNIQUE(project_id,id),
      CHECK(state IN ('PREPARED','STARTING','RUNNING','CANCELLING','SUCCEEDED','FAILED','TIMED_OUT','CANCELLED','UNKNOWN'))
    )""",
    """CREATE TABLE platform.patch (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL, workspace_id uuid NOT NULL, grant_id uuid NOT NULL,
      base_manifest_id uuid NOT NULL, expected_manifest_id uuid NOT NULL, workspace_manifest_id uuid NOT NULL,
      patch_artifact_id uuid NOT NULL, patch_digest platform.sha256_digest NOT NULL, test_evidence_digest platform.sha256_digest,
      state text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), row_version bigint NOT NULL DEFAULT 1,
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id), FOREIGN KEY(project_id,workspace_id) REFERENCES platform.workspace(project_id,id),
      FOREIGN KEY(project_id,grant_id) REFERENCES platform.workspace_grant(project_id,id), FOREIGN KEY(project_id,base_manifest_id) REFERENCES platform.manifest(project_id,id),
      FOREIGN KEY(project_id,expected_manifest_id) REFERENCES platform.manifest(project_id,id), FOREIGN KEY(project_id,workspace_manifest_id) REFERENCES platform.manifest(project_id,id),
      FOREIGN KEY(project_id,patch_artifact_id) REFERENCES platform.artifact(project_id,id), UNIQUE(project_id,id), UNIQUE(project_id,patch_digest),
      CHECK(state IN ('GENERATED','TESTED','AWAITING_APPROVAL','APPROVED','APPLYING','APPLIED','REJECTED','CONFLICT','APPLY_RECOVERY_REQUIRED','ROLLED_BACK'))
    )""",
    """CREATE TABLE platform.patch_apply (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, patch_id uuid NOT NULL, approval_request_id uuid NOT NULL,
      invocation_intent_id uuid NOT NULL, actual_manifest_id uuid NOT NULL, expected_manifest_digest platform.sha256_digest NOT NULL,
      actual_manifest_digest platform.sha256_digest NOT NULL, before_image_artifact_id uuid, journal_artifact_id uuid,
      status text NOT NULL, current_step integer NOT NULL DEFAULT 0, error_code text, started_at timestamptz NOT NULL DEFAULT clock_timestamp(), ended_at timestamptz,
      FOREIGN KEY(project_id,patch_id) REFERENCES platform.patch(project_id,id), FOREIGN KEY(project_id,approval_request_id) REFERENCES platform.approval_request(project_id,id),
      FOREIGN KEY(project_id,invocation_intent_id) REFERENCES platform.invocation_intent(project_id,id), FOREIGN KEY(project_id,actual_manifest_id) REFERENCES platform.manifest(project_id,id),
      FOREIGN KEY(project_id,before_image_artifact_id) REFERENCES platform.artifact(project_id,id), FOREIGN KEY(project_id,journal_artifact_id) REFERENCES platform.artifact(project_id,id),
      UNIQUE(project_id,id), CHECK(status IN ('PRECHECK','APPLYING','APPLIED','CONFLICT','APPLY_RECOVERY_REQUIRED','ROLLED_BACK','MANUALLY_COMPLETED'))
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass