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


class AuditEventResponse(BaseModel):
    action: str
    actor_id: str
    payload: Dict[str, Any]
    created_at: str


class HomeResponse(BaseModel):
    app_name: str
    version: str
    message: str
    api_prefix: str
    capabilities: List[str]
    endpoints: List[str]
