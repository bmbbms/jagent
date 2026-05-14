from fastapi import APIRouter, Depends

from app.agents.router import RouterAgent
from app.dependencies import (
    get_approval_service,
    get_audit_service,
    get_chat_service,
    get_router_agent,
)
from app.schemas import ChatRequest, ChatResponse, CreateApprovalRequest
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    router_agent: RouterAgent = Depends(get_router_agent),
    audit_service: AuditService = Depends(get_audit_service),
    approval_service: ApprovalService = Depends(get_approval_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    response = router_agent.run(request)

    if response.requires_approval:
        task = approval_service.create(
            CreateApprovalRequest(
                title=f"{response.capability_name} 审批确认",
                biz_domain=response.domain,
                requested_by=request.user_id,
                risk_level="high",
                capability_id=response.capability_id,
                workflow=response.workflow,
                payload={
                    "message": request.message,
                    "selected_skills": response.selected_skills,
                },
            )
        )
        response.approval_id = task.approval_id

    audit_service.record(
        action="chat.request",
        actor_id=request.user_id,
        payload={
            "biz_domain": request.biz_domain.value,
            "message": request.message,
            "capability_id": response.capability_id,
            "approval_id": response.approval_id,
            "selected_skills": response.selected_skills,
        },
    )

    chat_service.record_exchange(
        user_id=request.user_id,
        biz_domain=request.biz_domain,
        user_message=request.message,
        assistant_message=response.summary,
        assistant_metadata=response.model_dump(mode="json"),
    )

    return response
