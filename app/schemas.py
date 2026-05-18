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
    title: str
    biz_domain: BizDomain
    status: ApprovalStatus
    risk_level: str
    requested_by: str
    capability_id: Optional[str] = None
    workflow: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


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


class SkillInfo(BaseModel):
    skill_id: str
    biz_domain: BizDomain
    name: str
    path: str
    purpose: str = ""
    when_to_use: List[str] = Field(default_factory=list)


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
    tool_calls: List["ToolCallLogResponse"] = Field(default_factory=list)
    data_access_logs: List["DataAccessLogResponse"] = Field(default_factory=list)
    structured_tool_results: List["StructuredToolResultResponse"] = Field(default_factory=list)
    evaluation: Optional["AgentEvaluationResponse"] = None


class ToolCallLogResponse(BaseModel):
    tool_call_id: str
    task_id: str
    event_id: Optional[str] = None
    agent_id: Optional[str] = None
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
    status: str
    output_summary: str = ""
    request_query: str = ""
    request_kwargs: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    data_access_records: List[Dict[str, Any]] = Field(default_factory=list)
    event_time: Optional[str] = None


class AgentEvaluationDetailResponse(BaseModel):
    dimension_code: str
    dimension_name: str
    score: float
    problem_type: Optional[str] = None
    evidence: str = ""
    suggestion: str = ""
    severity: Optional[str] = None


class AgentOptimizationSuggestionResponse(BaseModel):
    optimization_type: str
    target_ref: Optional[str] = None
    current_value_summary: str = ""
    suggested_change: str
    priority: str
    status: str
    owner: Optional[str] = None


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


class HomeResponse(BaseModel):
    app_name: str
    version: str
    message: str
    api_prefix: str
    capabilities: List[str]
    endpoints: List[str]
