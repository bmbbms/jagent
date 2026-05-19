from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

AUTO_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class AgentRegistryModel(Base):
    __tablename__ = "t_agent_registry"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(128))
    agent_type: Mapped[str] = mapped_column(String(32))
    biz_domain: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    runtime_type: Mapped[str] = mapped_column(String(32), default="agentscope")
    invoke_mode: Mapped[str] = mapped_column(String(16), default="local")
    endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AgentSkillBindingModel(Base):
    __tablename__ = "t_agent_skill_binding"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    skill_id: Mapped[str] = mapped_column(String(64))
    skill_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(default=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentToolBindingModel(Base):
    __tablename__ = "t_agent_tool_binding"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_id: Mapped[str] = mapped_column(String(64))
    tool_type: Mapped[str] = mapped_column(String(32))
    permission_scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExternalCapabilityRegistryModel(Base):
    __tablename__ = "t_external_capability_registry"

    capability_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    capability_name: Mapped[str] = mapped_column(String(128))
    biz_domain: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(String(1024), default="")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    triggers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    requires_approval: Mapped[bool] = mapped_column(default=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    transport: Mapped[str] = mapped_column(String(32), default="http")
    endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service_host: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_path: Mapped[str] = mapped_column(String(255), default="/api/chat")
    extras: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    health_status: Mapped[str] = mapped_column(String(32), default="unknown")
    last_check_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_failure_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ContactModel(Base):
    __tablename__ = "t_contact_list"

    contact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contact_name: Mapped[str] = mapped_column(String(256))
    contact_type: Mapped[str] = mapped_column(String(16), default="conversation")
    channel: Mapped[str] = mapped_column(String(16), default="api")
    app_id: Mapped[str] = mapped_column(String(64), default="default")
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    biz_domain: Mapped[str] = mapped_column(String(64), default="merchant", index=True)
    external_contact_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_msg_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    round_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContactMessageModel(Base):
    __tablename__ = "t_contact_msg_list"

    msg_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contact_id: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    app_id: Mapped[str] = mapped_column(String(64), default="default")
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    msg_role: Mapped[str] = mapped_column(String(16))
    msg_type: Mapped[str] = mapped_column(String(32), default="text")
    message_phase: Mapped[str] = mapped_column(String(32), default="final")
    msg_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_files: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_msg_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    round_no: Mapped[int] = mapped_column(Integer, default=0)
    seq_no: Mapped[int] = mapped_column(BigInteger, default=0)
    is_visible: Mapped[bool] = mapped_column(default=True)
    workflow_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_msg_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    token_cnt: Mapped[int] = mapped_column(Integer, default=0)
    usage_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1)
    error_info: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentTaskModel(Base):
    __tablename__ = "t_agent_task"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contact_id: Mapped[str] = mapped_column(String(64), index=True)
    root_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    app_id: Mapped[str] = mapped_column(String(64), default="default")
    biz_domain: Mapped[str] = mapped_column(String(64), index=True)
    requested_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selected_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    runtime_type: Mapped[str] = mapped_column(String(32), default="agentscope")
    status: Mapped[str] = mapped_column(String(32), index=True)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    task_goal: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    approval_required: Mapped[bool] = mapped_column(default=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


class AgentTaskEventModel(Base):
    __tablename__ = "t_agent_task_event"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    event_seq: Mapped[int] = mapped_column(BigInteger)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_status: Mapped[str] = mapped_column(String(32), default="success")
    visible_to_user: Mapped[bool] = mapped_column(default=True)
    artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    event_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AgentTaskArtifactModel(Base):
    __tablename__ = "t_agent_task_artifact"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(32))
    artifact_name: Mapped[str] = mapped_column(String(256))
    artifact_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_type: Mapped[str] = mapped_column(String(16), default="db")
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    is_final: Mapped[bool] = mapped_column(default=False)
    visible_to_user: Mapped[bool] = mapped_column(default=True)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "t_audit_log"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default")
    source: Mapped[str] = mapped_column(String(32), default="platform")
    event_type: Mapped[str] = mapped_column(String(32), default="audit")
    op_type: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    cust_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    capability_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resp_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    outcome: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    response_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AgentObservationLogModel(Base):
    __tablename__ = "t_agent_observation_log"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    runtime_name: Mapped[str] = mapped_column(String(32), default="agentscope")
    call_type: Mapped[str] = mapped_column(String(32))
    phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    first_token_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="success")
    fallback_used: Mapped[bool] = mapped_column(default=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    input_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ToolCallLogModel(Base):
    __tablename__ = "t_tool_call_log"

    tool_call_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_name: Mapped[str] = mapped_column(String(128))
    tool_type: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sensitive_hit: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DataAccessLogModel(Base):
    __tablename__ = "t_data_access_log"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_source: Mapped[str] = mapped_column(String(128), index=True)
    data_object: Mapped[str] = mapped_column(String(256))
    access_type: Mapped[str] = mapped_column(String(16))
    sensitive_level: Mapped[str] = mapped_column(String(16), default="low")
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    field_scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskAuditLogModel(Base):
    __tablename__ = "t_risk_audit_log"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_type: Mapped[str] = mapped_column(String(64), index=True)
    risk_level: Mapped[str] = mapped_column(String(16))
    policy_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision: Mapped[str] = mapped_column(String(16))
    decision_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    hit_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_required: Mapped[bool] = mapped_column(default=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApprovalTaskModel(Base):
    __tablename__ = "t_approval_task"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    contact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biz_domain: Mapped[str] = mapped_column(String(64), index=True)
    approval_type: Mapped[str] = mapped_column(String(32), default="manual_review")
    title: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    risk_level: Mapped[str] = mapped_column(String(16))
    requested_by: Mapped[str] = mapped_column(String(64), index=True)
    current_approver: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capability_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApprovalAuditLogModel(Base):
    __tablename__ = "t_approval_audit_log"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    approval_id: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))
    operator_id: Mapped[str] = mapped_column(String(64))
    operator_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentEvaluationModel(Base):
    __tablename__ = "t_agent_evaluation"

    evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    evaluator_agent_id: Mapped[str] = mapped_column(String(64))
    evaluation_mode: Mapped[str] = mapped_column(String(16), default="online")
    overall_score: Mapped[float] = mapped_column(default=0.0)
    completion_score: Mapped[float] = mapped_column(default=0.0)
    accuracy_score: Mapped[float] = mapped_column(default=0.0)
    tool_usage_score: Mapped[float] = mapped_column(default=0.0)
    efficiency_score: Mapped[float] = mapped_column(default=0.0)
    compliance_score: Mapped[float] = mapped_column(default=0.0)
    user_feedback_score: Mapped[float] = mapped_column(default=0.0)
    cost_score: Mapped[float] = mapped_column(default=0.0)
    result_label: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentEvaluationDetailModel(Base):
    __tablename__ = "t_agent_evaluation_detail"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True)
    dimension_code: Mapped[str] = mapped_column(String(64))
    dimension_name: Mapped[str] = mapped_column(String(128))
    score: Mapped[float] = mapped_column(default=0.0)
    problem_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AgentOptimizationSuggestionModel(Base):
    __tablename__ = "t_agent_optimization_suggestion"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    optimization_type: Mapped[str] = mapped_column(String(32))
    target_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_value_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_change: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="new")
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ticket_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KnowledgeDocumentModel(Base):
    __tablename__ = "t_knowledge_document"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    biz_domain: Mapped[str] = mapped_column(String(64), index=True)
    doc_name: Mapped[str] = mapped_column(String(256))
    doc_type: Mapped[str] = mapped_column(String(32))
    source_type: Mapped[str] = mapped_column(String(32))
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="active")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KnowledgeChunkModel(Base):
    __tablename__ = "t_knowledge_chunk"

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_no: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vector_ref_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MerchantProfileModel(Base):
    __tablename__ = "t_merchant_profile"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_name: Mapped[str] = mapped_column(String(256), index=True)
    biz_domain: Mapped[str] = mapped_column(String(64), default="merchant", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    industry_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    register_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MerchantTransactionDailyModel(Base):
    __tablename__ = "t_merchant_transaction_daily"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    stat_date: Mapped[str] = mapped_column(String(10), index=True)
    txn_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    refund_count: Mapped[int] = mapped_column(Integer, default=0)
    gmv_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    refund_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MerchantRiskTagModel(Base):
    __tablename__ = "t_merchant_risk_tag"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    risk_tag: Mapped[str] = mapped_column(String(64), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    source_system: Mapped[str] = mapped_column(String(64), default="jagent")
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ServiceTicketModel(Base):
    __tablename__ = "t_service_ticket"

    ticket_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    biz_domain: Mapped[str] = mapped_column(String(64), default="operations", index=True)
    category: Mapped[str] = mapped_column(String(64), default="general", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True)
    requested_by: Mapped[str] = mapped_column(String(64), default="system", index=True)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="internal_tool")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DirectSalesMetricDailyModel(Base):
    __tablename__ = "t_direct_sales_metric_daily"

    id: Mapped[int] = mapped_column(AUTO_ID_TYPE, primary_key=True, autoincrement=True)
    stat_date: Mapped[str] = mapped_column(String(10), index=True)
    region_code: Mapped[str] = mapped_column(String(64), default="national", index=True)
    sales_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    merchant_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ReportExportJobModel(Base):
    __tablename__ = "t_report_export_job"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    report_type: Mapped[str] = mapped_column(String(64), default="compliance", index=True)
    biz_domain: Mapped[str] = mapped_column(String(64), default="data_support", index=True)
    format: Mapped[str] = mapped_column(String(16), default="xlsx")
    status: Mapped[str] = mapped_column(String(32), default="generated", index=True)
    requested_by: Mapped[str] = mapped_column(String(64), default="system", index=True)
    output_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
