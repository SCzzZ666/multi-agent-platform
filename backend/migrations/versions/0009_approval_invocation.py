r"""迁移第⑧步：approval_request / approval_decision / invocation_intent / invocation_receipt。"""
from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.approval_request (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL, node_attempt_id uuid NOT NULL,
      action_id uuid NOT NULL CHECK(platform.is_uuid_v7(action_id)), tool_schema_version_id uuid, workflow_digest platform.sha256_digest NOT NULL,
      schema_digest platform.sha256_digest NOT NULL, args_digest platform.sha256_digest NOT NULL, resources_digest platform.sha256_digest NOT NULL,
      risk text NOT NULL, status text NOT NULL, expires_at timestamptz NOT NULL, max_uses integer NOT NULL DEFAULT 1 CHECK(max_uses>0),
      used_count integer NOT NULL DEFAULT 0 CHECK(used_count>=0 AND used_count<=max_uses), row_version bigint NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), revoked_at timestamptz,
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      FOREIGN KEY(project_id,node_attempt_id) REFERENCES platform.node_attempt(project_id,id),
      FOREIGN KEY(project_id,tool_schema_version_id) REFERENCES platform.tool_schema_version(project_id,id),
      UNIQUE(project_id,id), UNIQUE(project_id,action_id),
      CHECK(status IN ('PENDING','APPROVED','CONSUMED','REJECTED','EXPIRED','REVOKED'))
    )""",
    """CREATE TABLE platform.approval_decision (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, approval_request_id uuid NOT NULL,
      decision text NOT NULL CHECK(decision IN ('APPROVE','REJECT','REVOKE')), decided_by uuid NOT NULL REFERENCES platform.app_user(id),
      idempotency_key text NOT NULL, request_digest platform.sha256_digest NOT NULL, reason text,
      decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,approval_request_id) REFERENCES platform.approval_request(project_id,id),
      UNIQUE(project_id,id), UNIQUE(approval_request_id,idempotency_key)
    )""",
    """CREATE TABLE platform.invocation_intent (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL, node_attempt_id uuid NOT NULL,
      approval_request_id uuid, action_id uuid NOT NULL CHECK(platform.is_uuid_v7(action_id)), tool_schema_version_id uuid,
      schema_digest platform.sha256_digest NOT NULL, args_digest platform.sha256_digest NOT NULL, resources_digest platform.sha256_digest NOT NULL,
      idempotency_class text NOT NULL CHECK(idempotency_class IN ('READ_ONLY','PLATFORM_IDEMPOTENT','PROVIDER_IDEMPOTENT','NON_IDEMPOTENT')),
      provider_key text, fencing_token bigint NOT NULL CHECK(fencing_token>0), status text NOT NULL,
      dispatch_not_before timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      FOREIGN KEY(project_id,node_attempt_id) REFERENCES platform.node_attempt(project_id,id),
      FOREIGN KEY(project_id,approval_request_id) REFERENCES platform.approval_request(project_id,id),
      FOREIGN KEY(project_id,tool_schema_version_id) REFERENCES platform.tool_schema_version(project_id,id),
      UNIQUE(project_id,id), UNIQUE(project_id,action_id), UNIQUE(project_id,provider_key),
      CHECK(status IN ('COMMITTED','DISPATCHED','SUCCEEDED','FAILED','UNKNOWN','RECONCILING','RECOVERY_REQUIRED'))
    )""",
    """CREATE TABLE platform.invocation_receipt (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, invocation_intent_id uuid NOT NULL,
      receipt_seq integer NOT NULL CHECK(receipt_seq>0), outcome text NOT NULL CHECK(outcome IN ('SUCCEEDED','FAILED','UNKNOWN','RECONCILED_SUCCEEDED','RECONCILED_FAILED')),
      provider_operation_id text, result_digest platform.sha256_digest, error_code text, received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,invocation_intent_id) REFERENCES platform.invocation_intent(project_id,id),
      UNIQUE(project_id,id), UNIQUE(invocation_intent_id,receipt_seq)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass