r"""迁移第⑥步（run 核心表族 + outbox）：run_snapshot/run/run_plan_version/run_lease/node_attempt/checkpoint/run_event/event_outbox。"""
from __future__ import annotations

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.run_snapshot (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      workflow_version_id uuid NOT NULL, source_snapshot jsonb NOT NULL, model_config_snapshot jsonb NOT NULL,
      prompt_snapshot jsonb NOT NULL, capability_snapshot jsonb NOT NULL, content_digest platform.sha256_digest NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(project_id,id), UNIQUE(project_id,content_digest),
      FOREIGN KEY(project_id,workflow_version_id) REFERENCES platform.workflow_version(project_id,id)
    )""",
    """CREATE TABLE platform.run (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      workflow_version_id uuid NOT NULL, run_snapshot_id uuid NOT NULL, state text NOT NULL,
      state_version bigint NOT NULL DEFAULT 0 CHECK(state_version>=0), event_seq bigint NOT NULL DEFAULT 0 CHECK(event_seq>=0),
      priority integer NOT NULL DEFAULT 100, max_wall_seconds integer NOT NULL CHECK(max_wall_seconds>0),
      max_cost_minor bigint NOT NULL DEFAULT 0 CHECK(max_cost_minor>=0), used_cost_minor bigint NOT NULL DEFAULT 0 CHECK(used_cost_minor>=0),
      cancel_deadline timestamptz, queued_at timestamptz NOT NULL DEFAULT clock_timestamp(), started_at timestamptz, ended_at timestamptz,
      updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      active_plan_version_id uuid, row_version bigint NOT NULL DEFAULT 1, UNIQUE(project_id,id),
      FOREIGN KEY(project_id,workflow_version_id) REFERENCES platform.workflow_version(project_id,id),
      FOREIGN KEY(project_id,run_snapshot_id) REFERENCES platform.run_snapshot(project_id,id),
      CHECK(state IN ('QUEUED','RUNNING','WAITING_APPROVAL','PAUSING','PAUSED','CANCELLING','CANCELLED','RECOVERY_REQUIRED','FAILED','SUCCEEDED'))
    )""",
    "ALTER TABLE platform.artifact ADD CONSTRAINT artifact_run_fk FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id)",
    """CREATE TABLE platform.run_plan_version (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL,
      plan_no integer NOT NULL CHECK(plan_no>0), task_plan_artifact_id uuid NOT NULL,
      validation_result_artifact_id uuid NOT NULL, compiled_graph_artifact_id uuid,
      compiled_graph_digest platform.sha256_digest, effective_limits_json jsonb NOT NULL,
      status text NOT NULL CHECK(status IN ('REJECTED','VALIDATED','COMPILED')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      FOREIGN KEY(project_id,task_plan_artifact_id) REFERENCES platform.artifact(project_id,id),
      FOREIGN KEY(project_id,validation_result_artifact_id) REFERENCES platform.artifact(project_id,id),
      FOREIGN KEY(project_id,compiled_graph_artifact_id) REFERENCES platform.artifact(project_id,id),
      UNIQUE(project_id,id), UNIQUE(run_id,plan_no),
      CHECK((status='REJECTED' AND compiled_graph_artifact_id IS NULL AND compiled_graph_digest IS NULL)
         OR (status='VALIDATED')
         OR (status='COMPILED' AND compiled_graph_artifact_id IS NOT NULL AND compiled_graph_digest IS NOT NULL))
    )""",
    "ALTER TABLE platform.run ADD CONSTRAINT run_active_plan_fk FOREIGN KEY(project_id,active_plan_version_id) REFERENCES platform.run_plan_version(project_id,id)",
    """CREATE TABLE platform.run_lease (
      run_id uuid PRIMARY KEY REFERENCES platform.run(id) ON DELETE CASCADE,
      lease_owner text NOT NULL, fencing_token bigint NOT NULL CHECK(fencing_token>0),
      heartbeat_at timestamptz NOT NULL, expires_at timestamptz NOT NULL CHECK(expires_at>heartbeat_at), row_version bigint NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE platform.node_attempt (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL,
      run_plan_version_id uuid, node_key text NOT NULL, task_id text NOT NULL, role_ref text NOT NULL,
      attempt_no integer NOT NULL CHECK(attempt_no>0), rework_round integer NOT NULL DEFAULT 0 CHECK(rework_round>=0),
      previous_attempt_id uuid, input_envelope_artifact_id uuid, input_digest platform.sha256_digest,
      result_envelope_artifact_id uuid, result_digest platform.sha256_digest, state text NOT NULL,
      fencing_token bigint NOT NULL CHECK(fencing_token>0), state_version bigint NOT NULL DEFAULT 0,
      completion_receipt platform.sha256_digest, error_code text, ready_at timestamptz, started_at timestamptz, ended_at timestamptz,
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      FOREIGN KEY(project_id,run_plan_version_id) REFERENCES platform.run_plan_version(project_id,id),
      FOREIGN KEY(project_id,previous_attempt_id) REFERENCES platform.node_attempt(project_id,id),
      FOREIGN KEY(project_id,input_envelope_artifact_id) REFERENCES platform.artifact(project_id,id),
      FOREIGN KEY(project_id,result_envelope_artifact_id) REFERENCES platform.artifact(project_id,id),
      UNIQUE(project_id,id), UNIQUE(run_id,node_key,attempt_no),
      CHECK((input_envelope_artifact_id IS NULL) = (input_digest IS NULL)),
      CHECK((result_envelope_artifact_id IS NULL) = (result_digest IS NULL)),
      CHECK(state IN ('READY','RUNNING','WAITING_APPROVAL','SUCCEEDED','FAILED','CANCELLED','SKIPPED','UNKNOWN'))
    )""",
    """CREATE TABLE platform.checkpoint (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL,
      checkpoint_seq bigint NOT NULL CHECK(checkpoint_seq>=0), framework text NOT NULL DEFAULT 'MAF' CHECK(framework='MAF'),
      framework_version text NOT NULL, serializer_version text NOT NULL, definition_digest platform.sha256_digest NOT NULL,
      state_version bigint NOT NULL CHECK(state_version>=0), object_ref text NOT NULL, content_digest platform.sha256_digest NOT NULL,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      UNIQUE(project_id,id), UNIQUE(run_id,checkpoint_seq)
    )""",
    """CREATE TABLE platform.run_event (
      id uuid PRIMARY KEY CHECK (platform.is_uuid_v7(id)), project_id uuid NOT NULL, run_id uuid NOT NULL,
      event_seq bigint NOT NULL CHECK(event_seq>0), event_type text NOT NULL, state_version bigint NOT NULL CHECK(state_version>=0),
      actor jsonb NOT NULL, correlation_id text NOT NULL, payload jsonb NOT NULL, payload_digest platform.sha256_digest NOT NULL,
      occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(), FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id),
      UNIQUE(project_id,id), UNIQUE(run_id,event_seq)
    )""",
    """CREATE TABLE platform.event_outbox (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      aggregate_type text NOT NULL, aggregate_id uuid NOT NULL, event_id uuid NOT NULL REFERENCES platform.run_event(id),
      available_at timestamptz NOT NULL DEFAULT clock_timestamp(), published_at timestamptz, attempts integer NOT NULL DEFAULT 0,
      last_error_code text, UNIQUE(event_id)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass