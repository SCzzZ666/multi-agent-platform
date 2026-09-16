r"""迁移第⑪步：高频索引 + 不可变触发器 + RLS（纵深防御，应用鉴权仍必需）。"""
from __future__ import annotations

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_INDEXES = [
    "CREATE INDEX run_queue_idx ON platform.run(project_id,priority,queued_at) WHERE state='QUEUED'",
    "CREATE INDEX run_active_idx ON platform.run(project_id,state,updated_at) WHERE state NOT IN ('CANCELLED','FAILED','SUCCEEDED')",
    "CREATE INDEX run_lease_expiry_idx ON platform.run_lease(expires_at)",
    "CREATE INDEX node_attempt_ready_idx ON platform.node_attempt(project_id,run_id,ready_at,node_key) WHERE state='READY'",
    "CREATE INDEX run_plan_lookup_idx ON platform.run_plan_version(project_id,run_id,plan_no DESC)",
    "CREATE INDEX node_attempt_plan_idx ON platform.node_attempt(project_id,run_plan_version_id,task_id,attempt_no)",
    "CREATE INDEX run_event_replay_idx ON platform.run_event(run_id,event_seq)",
    "CREATE INDEX run_event_project_time_idx ON platform.run_event(project_id,occurred_at DESC)",
    "CREATE INDEX outbox_pending_idx ON platform.event_outbox(available_at) WHERE published_at IS NULL",
    "CREATE INDEX approval_pending_idx ON platform.approval_request(project_id,expires_at) WHERE status='PENDING'",
    "CREATE INDEX invocation_unknown_idx ON platform.invocation_intent(project_id,updated_at) WHERE status='UNKNOWN'",
    "CREATE INDEX patch_recovery_idx ON platform.patch(project_id,created_at) WHERE state='APPLY_RECOVERY_REQUIRED'",
    "CREATE INDEX audit_time_idx ON platform.audit_event(project_id,occurred_at DESC)",
]

_TRIGGERS = [
    "CREATE OR REPLACE FUNCTION platform.reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable row: %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME USING ERRCODE='55000'; END $$",
    "CREATE TRIGGER workflow_version_immutable BEFORE UPDATE OR DELETE ON platform.workflow_version FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
    "CREATE TRIGGER workflow_template_version_immutable BEFORE UPDATE OR DELETE ON platform.workflow_template_version FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
    "CREATE TRIGGER run_plan_version_immutable BEFORE UPDATE OR DELETE ON platform.run_plan_version FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
    "CREATE TRIGGER run_event_immutable BEFORE UPDATE OR DELETE ON platform.run_event FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
    "CREATE TRIGGER audit_event_immutable BEFORE UPDATE OR DELETE ON platform.audit_event FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
    "CREATE TRIGGER invocation_receipt_immutable BEFORE UPDATE OR DELETE ON platform.invocation_receipt FOR EACH ROW EXECUTE FUNCTION platform.reject_immutable_change()",
]

_RLS = """
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['source','chat_thread','chat_message','proposal','workflow_draft','workflow_draft_revision','workflow_version',
    'artifact','run_snapshot','run','run_plan_version','node_attempt','checkpoint','run_event','event_outbox',
    'skill','skill_version','mcp_connection','credential_ref','tool_schema_version','capability_binding',
    'approval_request','approval_decision','invocation_intent','invocation_receipt','workspace_grant','workspace','manifest',
    'runner_task','patch','patch_apply','evidence','review','usage_record','audit_event'] LOOP
    EXECUTE format('ALTER TABLE platform.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('CREATE POLICY project_isolation ON platform.%I USING (project_id = platform.current_project_id()) WITH CHECK (project_id = platform.current_project_id())',t);
  END LOOP;
END $$
"""


def upgrade() -> None:
    for s in _INDEXES:
        op.execute(s)
    for s in _TRIGGERS:
        op.execute(s)
    op.execute(_RLS)


def downgrade() -> None:
    pass