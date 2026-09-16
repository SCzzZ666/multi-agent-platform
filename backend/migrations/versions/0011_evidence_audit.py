r"""迁移第⑩步：evidence / review / usage_record / audit_event。"""
from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_STMTS = [
    """CREATE TABLE platform.evidence (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      run_id uuid, artifact_id uuid, evidence_type text NOT NULL, subject_type text NOT NULL, subject_id uuid NOT NULL,
      subject_digest platform.sha256_digest, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id), FOREIGN KEY(project_id,artifact_id) REFERENCES platform.artifact(project_id,id), UNIQUE(project_id,id)
    )""",
    """CREATE TABLE platform.review (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id), artifact_id uuid NOT NULL,
      subject_digest platform.sha256_digest NOT NULL, decision text NOT NULL CHECK(decision IN ('PENDING','ACCEPTED','REJECTED','CHANGES_REQUESTED')),
      reviewer_id uuid REFERENCES platform.app_user(id), comments text, row_version bigint NOT NULL DEFAULT 1,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), decided_at timestamptz,
      FOREIGN KEY(project_id,artifact_id) REFERENCES platform.artifact(project_id,id), UNIQUE(project_id,id)
    )""",
    """CREATE TABLE platform.usage_record (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id), run_id uuid,
      provider_id text NOT NULL, model_ref text, usage_kind text NOT NULL, quantity numeric(20,6) NOT NULL CHECK(quantity>=0), unit text NOT NULL,
      cost_minor bigint CHECK(cost_minor>=0), currency char(3), occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(project_id,run_id) REFERENCES platform.run(project_id,id), UNIQUE(project_id,id)
    )""",
    """CREATE TABLE platform.audit_event (
      id uuid PRIMARY KEY CHECK(platform.is_uuid_v7(id)), project_id uuid NOT NULL REFERENCES platform.project(id),
      audit_seq bigint NOT NULL CHECK(audit_seq>0), event_type text NOT NULL, actor jsonb NOT NULL, subject jsonb NOT NULL,
      previous_digest platform.sha256_digest, event_digest platform.sha256_digest NOT NULL, payload_digest platform.sha256_digest NOT NULL,
      trace_id text NOT NULL, occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(project_id,id), UNIQUE(project_id,audit_seq), UNIQUE(project_id,event_digest)
    )""",
]


def upgrade() -> None:
    for s in _STMTS:
        op.execute(s)


def downgrade() -> None:
    pass