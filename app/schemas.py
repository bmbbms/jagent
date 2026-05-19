from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BizDomain(str, Enum):
    merchant = "merchant"
    operations = "operations"
    data_support = "data_support"
    partner = "partner"


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="发起请求的用户标识")
    biz_domain: BizDomain = Field(..., description="业务域")
    message: str = Field(..., min_length=1, description="用户消息")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingTrace(BaseModel):
    requested_domain: BizDomain
    selected_capability_id: str
    candidate_capability_ids: List[str] = Field(default_factory=list)
    matched_capability_ids: List[str] = Field(default_factory=list)
    declared_skills: List[str] = Field(default_factory=list)
    strategy: str = "priority_trigger_match"
    reason: str = ""


class ChatResponse(BaseModel):
    domain: BizDomain
    capability_id: str
    capability_name: str
    summary: str
    next_action: str
    selected_skills: List[str] = Field(default_factory=list)
    selected_tools: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    workflow: Optional[str] = None
    audit_tags: List[str] = Field(default_factory=list)
    approval_id: Optional[str] = None
    task_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    routing_trace: Optional[RoutingTrace] = None
    runtime_tool_results: List[Dict[str, Any]] = Field(default_factory=list, exclude=True)


class ApprovalDecision(str, Enum):
    approve = "approve"
    reject = "reject"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalTask(BaseModel):
    approval_id: str
    task_id: Optional[str] = None
    title: str
    biz_domain: BizDomain
    status: ApprovalStatus
    risk_level: str
    requested_by: str
    capability_id: Optional[str] = None
    workflow: Optional[str] = None
    reason: Optional[str] = None
    current_approver: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class CreateApprovalRequest(BaseModel):
    title: str
    biz_domain: BizDomain
    requested_by: str
    risk_level: str = "medium"
    capability_id: Optional[str] = None
    workflow: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    reviewer_id: str
    decision: ApprovalDecision
    comment: str = ""


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    status: ApprovalStatus
    reviewer_id: str
    decision: ApprovalDecision
    comment: str


class KnowledgeHit(BaseModel):
    title: str
    snippet: str
    source: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    biz_domain: BizDomain
    hits: List[KnowledgeHit]


class CapabilityInfo(BaseModel):
    capability_id: str
    capability_name: str
    biz_domain: BizDomain
    description: str
    priority: int
    triggers: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    source: str = "local"
    version: str = "v1"
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    transport: str = "inproc"
    endpoint: Optional[str] = None
    service_name: Optional[str] = None
    service_host: Optional[str] = None
    service_port: Optional[int] = None
    service_path: str = "/api/chat"
    extras: Dict[str, str] = Field(default_factory=dict)
    health_status: Optional[str] = None
    last_check_time: Optional[str] = None
    last_latency_ms: Optional[int] = None


class CapabilityOverviewResponse(BaseModel):
    total: int = 0
    local_count: int = 0
    external_count: int = 0
    approval_required_count: int = 0
    high_risk_count: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    unknown_health_count: int = 0
    domain_counts: Dict[str, int] = Field(default_factory=dict)
    source_counts: Dict[str, int] = Field(default_factory=dict)
    transport_counts: Dict[str, int] = Field(default_factory=dict)


class ExternalAgentRegisterRequest(BaseModel):
    capability_id: str
    capability_name: str
    biz_domain: BizDomain
    description: str
    priority: int = 100
    triggers: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    version: str = "v1"
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    transport: str = "http"
    endpoint: Optional[str] = None
    service_name: Optional[str] = None
    service_host: Optional[str] = None
    service_port: Optional[int] = None
    service_path: str = "/api/chat"
    extras: Dict[str, str] = Field(default_factory=dict)


class ExternalAgentUpdateRequest(BaseModel):
    capability_name: str
    biz_domain: BizDomain
    description: str
    priority: int = 100
    triggers: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    version: str = "v1"
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    transport: str = "http"
    endpoint: Optional[str] = None
    service_name: Optional[str] = None
    service_host: Optional[str] = None
    service_port: Optional[int] = None
    service_path: str = "/api/chat"
    extras: Dict[str, str] = Field(default_factory=dict)


class ExternalAgentAddRequest(BaseModel):
    agent_url: str
    biz_domain: BizDomain
    capability_id: Optional[str] = None
    capability_name: Optional[str] = None
    description: Optional[str] = None
    priority: int = 50
    triggers: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    transport: Optional[str] = None
    service_path: Optional[str] = None
    extras: Dict[str, str] = Field(default_factory=dict)


class ExternalAgentInfo(BaseModel):
    capability_id: str
    capability_name: str
    biz_domain: BizDomain
    description: str
    priority: int
    triggers: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    version: str = "v1"
    risk_level: str = "low"
    requires_approval: bool = False
    tags: List[str] = Field(default_factory=list)
    transport: str = "http"
    endpoint: Optional[str] = None
    service_name: Optional[str] = None
    service_host: Optional[str] = None
    service_port: Optional[int] = None
    service_path: str = "/api/chat"
    extras: Dict[str, str] = Field(default_factory=dict)
    source: str = "manual_remote"
    health_status: str = "unknown"
    last_check_time: Optional[str] = None
    last_success_time: Optional[str] = None
    last_failure_time: Optional[str] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    last_latency_ms: Optional[int] = None


class ExternalAgentHealthResponse(BaseModel):
    capability_id: str
    health_status: str = "unknown"
    last_check_time: Optional[str] = None
    last_success_time: Optional[str] = None
    last_failure_time: Optional[str] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    last_latency_ms: Optional[int] = None


class ExternalAgentHealthOverviewResponse(BaseModel):
    total: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0


class ExternalAgentGovernanceOverviewResponse(BaseModel):
    total: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0
    approval_required_count: int = 0
    high_risk_count: int = 0
    source_counts: Dict[str, int] = Field(default_factory=dict)
    transport_counts: Dict[str, int] = Field(default_factory=dict)
    domain_counts: Dict[str, int] = Field(default_factory=dict)


class MCPToolInfo(BaseModel):
    tool_id: str
    provider: str
    description: str = ""
    transport: str = "stdio"
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    enabled: bool = False
    config_path: Optional[str] = None
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_status: Optional[str] = None
    last_called_at: Optional[str] = None
    average_duration_ms: Optional[int] = None


class MCPToolOverviewResponse(BaseModel):
    total: int = 0
    enabled_count: int = 0
    provider_count: int = 0
    transport_count: int = 0
    called_tool_count: int = 0
    failure_tool_count: int = 0
    total_call_count: int = 0
    providers: List[str] = Field(default_factory=list)
    transports: List[str] = Field(default_factory=list)


class SkillInfo(BaseModel):
    skill_id: str
    biz_domain: BizDomain
    name: str
    path: str
    purpose: str = ""
    when_to_use: List[str] = Field(default_factory=list)


class SkillDetailInfo(SkillInfo):
    required_inputs: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    output_fields: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    human_escalation: List[str] = Field(default_factory=list)


class WorkflowStepResponse(BaseModel):
    step_code: str
    name: str
    step_type: str
    description: str
    required_tools: List[str] = Field(default_factory=list)
    approval_required: bool = False


class WorkflowDefinitionResponse(BaseModel):
    workflow_code: str
    name: str
    biz_domain: BizDomain
    purpose: str
    required_inputs: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    approval_points: List[str] = Field(default_factory=list)
    fallback_rules: List[str] = Field(default_factory=list)
    audit_tags: List[str] = Field(default_factory=list)
    steps: List[WorkflowStepResponse] = Field(default_factory=list)


class AuditEventResponse(BaseModel):
    action: str
    actor_id: str
    payload: Dict[str, Any]
    created_at: str
    source: Optional[str] = None
    event_type: Optional[str] = None
    outcome: Optional[int] = None
    task_id: Optional[str] = None
    approval_id: Optional[str] = None
    capability_id: Optional[str] = None
    workflow: Optional[str] = None
    ticket_id: Optional[str] = None
    suggestion_id: Optional[int] = None
    evaluation_id: Optional[str] = None


class AuditOverviewResponse(BaseModel):
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    source_counts: Dict[str, int] = Field(default_factory=dict)
    event_type_counts: Dict[str, int] = Field(default_factory=dict)
    action_counts: Dict[str, int] = Field(default_factory=dict)
    linked_context_counts: Dict[str, int] = Field(default_factory=dict)


class AgentTaskEventResponse(BaseModel):
    event_id: str
    event_type: str
    event_seq: int
    title: str = ""
    content: str = ""
    event_status: str
    visible_to_user: bool = True
    agent_id: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    event_payload: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskArtifactResponse(BaseModel):
    artifact_id: str
    artifact_type: str
    artifact_name: str
    artifact_summary: str = ""
    is_final: bool = False
    visible_to_user: bool = True
    content_snapshot: str = ""
    create_time: str


class AgentTaskDeliverableResponse(BaseModel):
    deliverable_id: str
    deliverable_type: str
    title: str
    summary: str = ""
    content: str = ""
    source_type: str = ""
    source_ref: Optional[str] = None
    agent_id: Optional[str] = None
    status: str = "success"
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    create_time: Optional[str] = None


class AgentTaskOutputOverviewResponse(BaseModel):
    task_id: str
    total_deliverables: int = 0
    final_output: str = ""
    next_action: str = ""
    deliverables: List[AgentTaskDeliverableResponse] = Field(default_factory=list)


class AgentTaskSummaryResponse(BaseModel):
    task_id: str
    contact_id: str
    user_id: str
    biz_domain: str
    selected_agent_id: Optional[str] = None
    status: str
    current_stage: Optional[str] = None
    task_title: str = ""
    task_goal: str = ""
    risk_level: str = "low"
    approval_required: bool = False
    approval_id: Optional[str] = None
    trace_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    final_output_summary: str = ""


class AgentTaskListResponse(BaseModel):
    items: List[AgentTaskSummaryResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    sort_by: str = "start_time"
    sort_order: str = "desc"
    has_next: bool = False


class AgentTaskDetailResponse(AgentTaskSummaryResponse):
    events: List[AgentTaskEventResponse] = Field(default_factory=list)
    artifacts: List[AgentTaskArtifactResponse] = Field(default_factory=list)
    output_overview: Optional["AgentTaskOutputOverviewResponse"] = None
    tool_calls: List["ToolCallLogResponse"] = Field(default_factory=list)
    data_access_logs: List["DataAccessLogResponse"] = Field(default_factory=list)
    structured_tool_results: List["StructuredToolResultResponse"] = Field(default_factory=list)
    observations: List["AgentObservationLogResponse"] = Field(default_factory=list)
    runtime_sessions: List["RuntimeSessionViewResponse"] = Field(default_factory=list)
    runtime_governance: Optional["TaskRuntimeGovernanceSummaryResponse"] = None
    evaluation: Optional["AgentEvaluationResponse"] = None


class ToolCallLogResponse(BaseModel):
    tool_call_id: str
    task_id: str
    event_id: Optional[str] = None
    agent_id: Optional[str] = None
    runtime_session_id: Optional[str] = None
    tool_id: str
    tool_name: str
    tool_type: str
    provider: Optional[str] = None
    request_args: Dict[str, Any] = Field(default_factory=dict)
    response_summary: str = ""
    status: str
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    sensitive_hit: bool = False
    duration_ms: Optional[int] = None
    start_time: str
    end_time: Optional[str] = None


class DataAccessLogResponse(BaseModel):
    id: int
    task_id: str
    agent_id: Optional[str] = None
    tool_call_id: Optional[str] = None
    runtime_session_id: Optional[str] = None
    data_source: str
    data_object: str
    access_type: str
    sensitive_level: str
    row_count: Optional[int] = None
    field_scope: Dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    approval_id: Optional[str] = None
    operator_id: Optional[str] = None
    create_time: str


class StructuredToolResultResponse(BaseModel):
    tool_call_id: str
    tool_id: str
    tool_name: str
    tool_type: str
    provider: Optional[str] = None
    agent_id: Optional[str] = None
    runtime_session_id: Optional[str] = None
    status: str
    output_summary: str = ""
    request_query: str = ""
    request_kwargs: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    data_access_records: List[Dict[str, Any]] = Field(default_factory=list)
    event_time: Optional[str] = None


class AgentObservationLogResponse(BaseModel):
    id: int
    task_id: str
    trace_id: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    runtime_name: str
    call_type: str
    phase: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: Optional[int] = None
    first_token_ms: Optional[int] = None
    status: str
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    input_snapshot: str = ""
    output_snapshot: str = ""
    extra_info: Dict[str, Any] = Field(default_factory=dict)
    start_time: str
    end_time: Optional[str] = None


class RuntimeSessionViewResponse(BaseModel):
    session_id: str
    trace_id: str
    agent_id: Optional[str] = None
    runtime_name: str
    phases: List[str] = Field(default_factory=list)
    statuses: List[str] = Field(default_factory=list)
    fallback_reasons: List[str] = Field(default_factory=list)
    total_latency_ms: int = 0
    observation_count: int = 0
    tool_call_count: int = 0
    data_access_count: int = 0
    observations: List["AgentObservationLogResponse"] = Field(default_factory=list)


class TaskRuntimeGovernanceSummaryResponse(BaseModel):
    runtime_session_count: int = 0
    observation_count: int = 0
    fallback_count: int = 0
    mcp_call_count: int = 0
    mcp_error_count: int = 0
    mcp_provider_count: int = 0
    mcp_providers: List[str] = Field(default_factory=list)
    external_agent_call_count: int = 0
    external_agent_error_count: int = 0
    agent_handoff_count: int = 0
    unique_agent_count: int = 0
    active_agents: List[str] = Field(default_factory=list)
    observed_phases: List[str] = Field(default_factory=list)
    fallback_reasons: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)


class AgentEvaluationDetailResponse(BaseModel):
    dimension_code: str
    dimension_name: str
    score: float
    problem_type: Optional[str] = None
    evidence: str = ""
    suggestion: str = ""
    severity: Optional[str] = None


class AgentOptimizationSuggestionResponse(BaseModel):
    suggestion_id: int
    optimization_type: str
    target_ref: Optional[str] = None
    current_value_summary: str = ""
    suggested_change: str
    priority: str
    status: str
    owner: Optional[str] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    ticket_id: Optional[str] = None
    ticket_status: Optional[str] = None
    closed_at: Optional[str] = None
    create_time: str = ""
    update_time: str = ""


class AgentOptimizationSuggestionUpdateRequest(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    priority: Optional[str] = None


class AgentOptimizationSuggestionTicketRequest(BaseModel):
    requested_by: str
    owner: Optional[str] = None
    priority: Optional[str] = None
    comment: str = ""


class AgentOptimizationSuggestionOverviewResponse(BaseModel):
    total: int = 0
    new_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    high_priority_count: int = 0
    ticket_bound_count: int = 0
    ticket_unbound_count: int = 0
    completed_ticket_count: int = 0
    backlog_count: int = 0
    high_priority_backlog_count: int = 0
    completion_rate: float = 0.0


class AgentEvaluationSummaryResponse(BaseModel):
    evaluation_id: str
    task_id: str
    agent_id: str
    evaluator_agent_id: str
    evaluation_mode: str
    overall_score: float
    completion_score: float
    accuracy_score: float
    tool_usage_score: float
    efficiency_score: float
    compliance_score: float
    user_feedback_score: float
    cost_score: float
    result_label: str
    summary: str = ""
    create_time: str


class AgentEvaluationResponse(AgentEvaluationSummaryResponse):
    details: List[AgentEvaluationDetailResponse] = Field(default_factory=list)
    suggestions: List[AgentOptimizationSuggestionResponse] = Field(default_factory=list)


class AgentEvaluationAnalyticsItemResponse(BaseModel):
    agent_id: str
    evaluation_count: int = 0
    excellent_count: int = 0
    good_count: int = 0
    poor_count: int = 0
    average_overall_score: float = 0.0
    average_efficiency_score: float = 0.0
    average_tool_usage_score: float = 0.0
    poor_rate: float = 0.0
    fallback_related_count: int = 0
    attention_level: str = "normal"


class AgentEvaluationAnalyticsOverviewResponse(BaseModel):
    evaluation_count: int = 0
    agent_count: int = 0
    poor_evaluation_count: int = 0
    high_attention_agent_count: int = 0
    average_overall_score: float = 0.0
    average_efficiency_score: float = 0.0
    average_tool_usage_score: float = 0.0


class AgentEvaluationFocusAgentResponse(BaseModel):
    agent_id: str
    attention_level: str = "normal"
    average_overall_score: float = 0.0
    evaluation_count: int = 0
    poor_rate: float = 0.0
    suggestion_count: int = 0
    backlog_suggestion_count: int = 0
    high_priority_backlog_count: int = 0
    ticket_bound_suggestion_count: int = 0
    completed_ticket_count: int = 0
    governance_score: float = 0.0
    focus_reason: str = ""


class AgentEvaluationTrendPointResponse(BaseModel):
    evaluation_id: str
    task_id: str
    agent_id: str
    overall_score: float
    result_label: str
    create_time: str


class AgentEvaluationTrendResponse(BaseModel):
    agent_id: Optional[str] = None
    evaluation_count: int = 0
    average_overall_score: float = 0.0
    latest_overall_score: float = 0.0
    previous_overall_score: Optional[float] = None
    score_delta: float = 0.0
    improving: bool = False
    poor_count: int = 0
    attention_level: str = "normal"
    points: List[AgentEvaluationTrendPointResponse] = Field(default_factory=list)


class ServiceTicketResponse(BaseModel):
    ticket_id: str
    merchant_id: Optional[str] = None
    biz_domain: str
    category: str
    priority: str
    title: str
    description: str = ""
    status: str
    requested_by: str
    owner: Optional[str] = None
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    create_time: str = ""
    update_time: str = ""
    closed_at: Optional[str] = None
    linked_suggestion_id: Optional[int] = None
    linked_evaluation_id: Optional[str] = None
    linked_agent_id: Optional[str] = None
    linked_task_id: Optional[str] = None


class ServiceTicketOverviewResponse(BaseModel):
    total: int = 0
    submitted_count: int = 0
    in_progress_count: int = 0
    resolved_count: int = 0
    closed_count: int = 0
    backlog_count: int = 0
    high_priority_count: int = 0
    unassigned_count: int = 0
    stale_open_count: int = 0
    evaluation_source_count: int = 0
    internal_tool_source_count: int = 0
    completion_rate: float = 0.0


class ServiceTicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    priority: Optional[str] = None


class HomeResponse(BaseModel):
    app_name: str
    version: str
    message: str
    api_prefix: str
    capabilities: List[str]
    endpoints: List[str]
