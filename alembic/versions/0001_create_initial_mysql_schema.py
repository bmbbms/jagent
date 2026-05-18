"""create initial mysql schema

Revision ID: 0001_create_initial_mysql_schema
Revises:
Create Date: 2026-05-18 11:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_create_initial_mysql_schema"
down_revision = None
branch_labels = None
depends_on = None

AUTO_ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "t_agent_registry",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("agent_type", sa.String(length=32), nullable=False),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("runtime_type", sa.String(length=32), nullable=False),
        sa.Column("invoke_mode", sa.String(length=16), nullable=False),
        sa.Column("endpoint", sa.String(length=512), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("owner", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("agent_id", name="uq_t_agent_registry_agent_id"),
    )
    op.create_index(
        "ix_t_agent_registry_agent_id", "t_agent_registry", ["agent_id"], unique=True
    )
    op.create_index(
        "ix_t_agent_registry_biz_domain",
        "t_agent_registry",
        ["biz_domain"],
        unique=False,
    )

    op.create_table(
        "t_agent_skill_binding",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=64), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_agent_skill_binding_agent_id",
        "t_agent_skill_binding",
        ["agent_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_tool_binding",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("tool_id", sa.String(length=64), nullable=False),
        sa.Column("tool_type", sa.String(length=32), nullable=False),
        sa.Column("permission_scope", sa.String(length=128), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_agent_tool_binding_agent_id",
        "t_agent_tool_binding",
        ["agent_id"],
        unique=False,
    )

    op.create_table(
        "t_contact_list",
        sa.Column("contact_id", sa.String(length=64), primary_key=True),
        sa.Column("contact_name", sa.String(length=256), nullable=False),
        sa.Column("contact_type", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("external_contact_id", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.String(length=1024), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("last_msg_id", sa.String(length=64), nullable=True),
        sa.Column("last_msg_time", sa.DateTime(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("round_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_contact_list_agent_id", "t_contact_list", ["agent_id"], unique=False
    )
    op.create_index(
        "ix_t_contact_list_biz_domain",
        "t_contact_list",
        ["biz_domain"],
        unique=False,
    )
    op.create_index(
        "ix_t_contact_list_user_id", "t_contact_list", ["user_id"], unique=False
    )

    op.create_table(
        "t_contact_msg_list",
        sa.Column("msg_id", sa.String(length=64), primary_key=True),
        sa.Column("contact_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("msg_role", sa.String(length=16), nullable=False),
        sa.Column("msg_type", sa.String(length=32), nullable=False),
        sa.Column("message_phase", sa.String(length=32), nullable=False),
        sa.Column("msg_content", sa.Text(), nullable=True),
        sa.Column("content_files", sa.JSON(), nullable=True),
        sa.Column("external_msg_id", sa.String(length=128), nullable=True),
        sa.Column("parent_msg_id", sa.String(length=64), nullable=True),
        sa.Column("ref_msg_id", sa.String(length=64), nullable=True),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("seq_no", sa.BigInteger(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("workflow_name", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("provider_msg_id", sa.String(length=128), nullable=True),
        sa.Column("token_cnt", sa.Integer(), nullable=False),
        sa.Column("usage_info", sa.JSON(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("error_info", sa.String(length=1024), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_contact_msg_list_agent_id",
        "t_contact_msg_list",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_contact_msg_list_contact_id",
        "t_contact_msg_list",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_contact_msg_list_create_time",
        "t_contact_msg_list",
        ["create_time"],
        unique=False,
    )
    op.create_index(
        "ix_t_contact_msg_list_task_id",
        "t_contact_msg_list",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_contact_msg_list_user_id",
        "t_contact_msg_list",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_task",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("contact_id", sa.String(length=64), nullable=False),
        sa.Column("root_msg_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("requested_agent_id", sa.String(length=64), nullable=True),
        sa.Column("selected_agent_id", sa.String(length=64), nullable=True),
        sa.Column("runtime_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=True),
        sa.Column("current_agent_id", sa.String(length=64), nullable=True),
        sa.Column("task_title", sa.String(length=256), nullable=True),
        sa.Column("task_goal", sa.String(length=1024), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("final_output_summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_t_agent_task_biz_domain", "t_agent_task", ["biz_domain"], unique=False
    )
    op.create_index(
        "ix_t_agent_task_contact_id", "t_agent_task", ["contact_id"], unique=False
    )
    op.create_index(
        "ix_t_agent_task_selected_agent_id",
        "t_agent_task",
        ["selected_agent_id"],
        unique=False,
    )
    op.create_index("ix_t_agent_task_status", "t_agent_task", ["status"], unique=False)
    op.create_index(
        "ix_t_agent_task_trace_id", "t_agent_task", ["trace_id"], unique=False
    )
    op.create_index(
        "ix_t_agent_task_user_id", "t_agent_task", ["user_id"], unique=False
    )

    op.create_table(
        "t_agent_task_event",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("contact_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_seq", sa.BigInteger(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("node_id", sa.String(length=64), nullable=True),
        sa.Column("parent_event_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("event_status", sa.String(length=32), nullable=False),
        sa.Column("visible_to_user", sa.Boolean(), nullable=False),
        sa.Column("artifact_id", sa.String(length=64), nullable=True),
        sa.Column("tool_call_id", sa.String(length=64), nullable=True),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("event_payload", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_t_agent_task_event_contact_id",
        "t_agent_task_event",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_task_event_event_type",
        "t_agent_task_event",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_task_event_task_id",
        "t_agent_task_event",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_task_artifact",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("contact_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("artifact_name", sa.String(length=256), nullable=False),
        sa.Column("artifact_summary", sa.String(length=1024), nullable=True),
        sa.Column("storage_type", sa.String(length=16), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("visible_to_user", sa.Boolean(), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_agent_task_artifact_agent_id",
        "t_agent_task_artifact",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_task_artifact_contact_id",
        "t_agent_task_artifact",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_task_artifact_task_id",
        "t_agent_task_artifact",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_audit_log",
        sa.Column("log_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("op_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("cust_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("span_id", sa.String(length=32), nullable=True),
        sa.Column("parent_span_id", sa.String(length=32), nullable=True),
        sa.Column("capability_id", sa.String(length=64), nullable=True),
        sa.Column("tool_id", sa.String(length=64), nullable=True),
        sa.Column("workflow_id", sa.String(length=64), nullable=True),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("request_summary", sa.Text(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("resp_code", sa.String(length=16), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_msg", sa.String(length=1024), nullable=True),
        sa.Column("outcome", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("request_time", sa.DateTime(), nullable=False),
        sa.Column("response_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_audit_log_agent_id", "t_audit_log", ["agent_id"], unique=False
    )
    op.create_index(
        "ix_t_audit_log_create_time", "t_audit_log", ["create_time"], unique=False
    )
    op.create_index("ix_t_audit_log_op_type", "t_audit_log", ["op_type"], unique=False)
    op.create_index("ix_t_audit_log_task_id", "t_audit_log", ["task_id"], unique=False)
    op.create_index(
        "ix_t_audit_log_trace_id", "t_audit_log", ["trace_id"], unique=False
    )
    op.create_index(
        "ix_t_audit_log_user_id", "t_audit_log", ["user_id"], unique=False
    )

    op.create_table(
        "t_agent_observation_log",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("runtime_name", sa.String(length=32), nullable=False),
        sa.Column("call_type", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=True),
        sa.Column("model_provider", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.BigInteger(), nullable=True),
        sa.Column("first_token_ms", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("fallback_reason", sa.String(length=512), nullable=True),
        sa.Column("input_snapshot", sa.Text(), nullable=True),
        sa.Column("output_snapshot", sa.Text(), nullable=True),
        sa.Column("extra_info", sa.JSON(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_t_agent_observation_log_agent_id",
        "t_agent_observation_log",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_observation_log_task_id",
        "t_agent_observation_log",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_observation_log_trace_id",
        "t_agent_observation_log",
        ["trace_id"],
        unique=False,
    )

    op.create_table(
        "t_tool_call_log",
        sa.Column("tool_call_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("tool_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("request_args", sa.JSON(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_msg", sa.String(length=1024), nullable=True),
        sa.Column("sensitive_hit", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_t_tool_call_log_task_id", "t_tool_call_log", ["task_id"], unique=False
    )
    op.create_index(
        "ix_t_tool_call_log_tool_id", "t_tool_call_log", ["tool_id"], unique=False
    )

    op.create_table(
        "t_data_access_log",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("tool_call_id", sa.String(length=64), nullable=True),
        sa.Column("data_source", sa.String(length=128), nullable=False),
        sa.Column("data_object", sa.String(length=256), nullable=False),
        sa.Column("access_type", sa.String(length=16), nullable=False),
        sa.Column("sensitive_level", sa.String(length=16), nullable=False),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("field_scope", sa.JSON(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("operator_id", sa.String(length=64), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_data_access_log_data_source",
        "t_data_access_log",
        ["data_source"],
        unique=False,
    )
    op.create_index(
        "ix_t_data_access_log_task_id",
        "t_data_access_log",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_risk_audit_log",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("risk_type", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("policy_code", sa.String(length=64), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("decision_reason", sa.String(length=1024), nullable=True),
        sa.Column("hit_rules", sa.JSON(), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_risk_audit_log_risk_type",
        "t_risk_audit_log",
        ["risk_type"],
        unique=False,
    )
    op.create_index(
        "ix_t_risk_audit_log_task_id",
        "t_risk_audit_log",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_approval_task",
        sa.Column("approval_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("contact_id", sa.String(length=64), nullable=True),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("approval_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("current_approver", sa.String(length=64), nullable=True),
        sa.Column("capability_id", sa.String(length=64), nullable=True),
        sa.Column("workflow_code", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("expire_time", sa.DateTime(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_approval_task_biz_domain",
        "t_approval_task",
        ["biz_domain"],
        unique=False,
    )
    op.create_index(
        "ix_t_approval_task_create_time",
        "t_approval_task",
        ["create_time"],
        unique=False,
    )
    op.create_index(
        "ix_t_approval_task_requested_by",
        "t_approval_task",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        "ix_t_approval_task_status", "t_approval_task", ["status"], unique=False
    )
    op.create_index(
        "ix_t_approval_task_task_id", "t_approval_task", ["task_id"], unique=False
    )

    op.create_table(
        "t_approval_audit_log",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("approval_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("operator_id", sa.String(length=64), nullable=False),
        sa.Column("operator_name", sa.String(length=128), nullable=True),
        sa.Column("comment", sa.String(length=1024), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_approval_audit_log_approval_id",
        "t_approval_audit_log",
        ["approval_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_approval_audit_log_task_id",
        "t_approval_audit_log",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_evaluation",
        sa.Column("evaluation_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("contact_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("evaluator_agent_id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_mode", sa.String(length=16), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("completion_score", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("tool_usage_score", sa.Float(), nullable=False),
        sa.Column("efficiency_score", sa.Float(), nullable=False),
        sa.Column("compliance_score", sa.Float(), nullable=False),
        sa.Column("user_feedback_score", sa.Float(), nullable=False),
        sa.Column("cost_score", sa.Float(), nullable=False),
        sa.Column("result_label", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=1024), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_agent_evaluation_agent_id",
        "t_agent_evaluation",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_evaluation_task_id",
        "t_agent_evaluation",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_evaluation_detail",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("evaluation_id", sa.String(length=64), nullable=False),
        sa.Column("dimension_code", sa.String(length=64), nullable=False),
        sa.Column("dimension_name", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("problem_type", sa.String(length=64), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
    )
    op.create_index(
        "ix_t_agent_evaluation_detail_evaluation_id",
        "t_agent_evaluation_detail",
        ["evaluation_id"],
        unique=False,
    )

    op.create_table(
        "t_agent_optimization_suggestion",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("evaluation_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("optimization_type", sa.String(length=32), nullable=False),
        sa.Column("target_ref", sa.String(length=128), nullable=True),
        sa.Column("current_value_summary", sa.Text(), nullable=True),
        sa.Column("suggested_change", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("owner", sa.String(length=64), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_agent_optimization_suggestion_agent_id",
        "t_agent_optimization_suggestion",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_agent_optimization_suggestion_evaluation_id",
        "t_agent_optimization_suggestion",
        ["evaluation_id"],
        unique=False,
    )

    op.create_table(
        "t_knowledge_document",
        sa.Column("doc_id", sa.String(length=64), primary_key=True),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("doc_name", sa.String(length=256), nullable=False),
        sa.Column("doc_type", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_knowledge_document_biz_domain",
        "t_knowledge_document",
        ["biz_domain"],
        unique=False,
    )

    op.create_table(
        "t_knowledge_chunk",
        sa.Column("chunk_id", sa.String(length=64), primary_key=True),
        sa.Column("doc_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_no", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_summary", sa.String(length=1024), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding_json", sa.JSON(), nullable=True),
        sa.Column("vector_ref_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_knowledge_chunk_doc_id", "t_knowledge_chunk", ["doc_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_t_knowledge_chunk_doc_id", table_name="t_knowledge_chunk")
    op.drop_table("t_knowledge_chunk")

    op.drop_index(
        "ix_t_knowledge_document_biz_domain", table_name="t_knowledge_document"
    )
    op.drop_table("t_knowledge_document")

    op.drop_index(
        "ix_t_agent_optimization_suggestion_evaluation_id",
        table_name="t_agent_optimization_suggestion",
    )
    op.drop_index(
        "ix_t_agent_optimization_suggestion_agent_id",
        table_name="t_agent_optimization_suggestion",
    )
    op.drop_table("t_agent_optimization_suggestion")

    op.drop_index(
        "ix_t_agent_evaluation_detail_evaluation_id",
        table_name="t_agent_evaluation_detail",
    )
    op.drop_table("t_agent_evaluation_detail")

    op.drop_index("ix_t_agent_evaluation_task_id", table_name="t_agent_evaluation")
    op.drop_index("ix_t_agent_evaluation_agent_id", table_name="t_agent_evaluation")
    op.drop_table("t_agent_evaluation")

    op.drop_index("ix_t_approval_audit_log_task_id", table_name="t_approval_audit_log")
    op.drop_index(
        "ix_t_approval_audit_log_approval_id", table_name="t_approval_audit_log"
    )
    op.drop_table("t_approval_audit_log")

    op.drop_index("ix_t_approval_task_task_id", table_name="t_approval_task")
    op.drop_index("ix_t_approval_task_status", table_name="t_approval_task")
    op.drop_index("ix_t_approval_task_requested_by", table_name="t_approval_task")
    op.drop_index("ix_t_approval_task_create_time", table_name="t_approval_task")
    op.drop_index("ix_t_approval_task_biz_domain", table_name="t_approval_task")
    op.drop_table("t_approval_task")

    op.drop_index("ix_t_risk_audit_log_task_id", table_name="t_risk_audit_log")
    op.drop_index("ix_t_risk_audit_log_risk_type", table_name="t_risk_audit_log")
    op.drop_table("t_risk_audit_log")

    op.drop_index("ix_t_data_access_log_task_id", table_name="t_data_access_log")
    op.drop_index(
        "ix_t_data_access_log_data_source", table_name="t_data_access_log"
    )
    op.drop_table("t_data_access_log")

    op.drop_index("ix_t_tool_call_log_tool_id", table_name="t_tool_call_log")
    op.drop_index("ix_t_tool_call_log_task_id", table_name="t_tool_call_log")
    op.drop_table("t_tool_call_log")

    op.drop_index(
        "ix_t_agent_observation_log_trace_id", table_name="t_agent_observation_log"
    )
    op.drop_index(
        "ix_t_agent_observation_log_task_id", table_name="t_agent_observation_log"
    )
    op.drop_index(
        "ix_t_agent_observation_log_agent_id", table_name="t_agent_observation_log"
    )
    op.drop_table("t_agent_observation_log")

    op.drop_index("ix_t_audit_log_user_id", table_name="t_audit_log")
    op.drop_index("ix_t_audit_log_trace_id", table_name="t_audit_log")
    op.drop_index("ix_t_audit_log_task_id", table_name="t_audit_log")
    op.drop_index("ix_t_audit_log_op_type", table_name="t_audit_log")
    op.drop_index("ix_t_audit_log_create_time", table_name="t_audit_log")
    op.drop_index("ix_t_audit_log_agent_id", table_name="t_audit_log")
    op.drop_table("t_audit_log")

    op.drop_index(
        "ix_t_agent_task_artifact_task_id", table_name="t_agent_task_artifact"
    )
    op.drop_index(
        "ix_t_agent_task_artifact_contact_id", table_name="t_agent_task_artifact"
    )
    op.drop_index(
        "ix_t_agent_task_artifact_agent_id", table_name="t_agent_task_artifact"
    )
    op.drop_table("t_agent_task_artifact")

    op.drop_index("ix_t_agent_task_event_task_id", table_name="t_agent_task_event")
    op.drop_index(
        "ix_t_agent_task_event_event_type", table_name="t_agent_task_event"
    )
    op.drop_index(
        "ix_t_agent_task_event_contact_id", table_name="t_agent_task_event"
    )
    op.drop_table("t_agent_task_event")

    op.drop_index("ix_t_agent_task_user_id", table_name="t_agent_task")
    op.drop_index("ix_t_agent_task_trace_id", table_name="t_agent_task")
    op.drop_index("ix_t_agent_task_status", table_name="t_agent_task")
    op.drop_index(
        "ix_t_agent_task_selected_agent_id", table_name="t_agent_task"
    )
    op.drop_index("ix_t_agent_task_contact_id", table_name="t_agent_task")
    op.drop_index("ix_t_agent_task_biz_domain", table_name="t_agent_task")
    op.drop_table("t_agent_task")

    op.drop_index("ix_t_contact_msg_list_user_id", table_name="t_contact_msg_list")
    op.drop_index("ix_t_contact_msg_list_task_id", table_name="t_contact_msg_list")
    op.drop_index(
        "ix_t_contact_msg_list_create_time", table_name="t_contact_msg_list"
    )
    op.drop_index(
        "ix_t_contact_msg_list_contact_id", table_name="t_contact_msg_list"
    )
    op.drop_index("ix_t_contact_msg_list_agent_id", table_name="t_contact_msg_list")
    op.drop_table("t_contact_msg_list")

    op.drop_index("ix_t_contact_list_user_id", table_name="t_contact_list")
    op.drop_index("ix_t_contact_list_biz_domain", table_name="t_contact_list")
    op.drop_index("ix_t_contact_list_agent_id", table_name="t_contact_list")
    op.drop_table("t_contact_list")

    op.drop_index(
        "ix_t_agent_tool_binding_agent_id", table_name="t_agent_tool_binding"
    )
    op.drop_table("t_agent_tool_binding")

    op.drop_index(
        "ix_t_agent_skill_binding_agent_id", table_name="t_agent_skill_binding"
    )
    op.drop_table("t_agent_skill_binding")

    op.drop_index("ix_t_agent_registry_biz_domain", table_name="t_agent_registry")
    op.drop_index("ix_t_agent_registry_agent_id", table_name="t_agent_registry")
    op.drop_table("t_agent_registry")
