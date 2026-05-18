from fastapi import APIRouter, Depends

from app.agents.router import RouterAgent
from app.dependencies import (
    get_approval_service,
    get_audit_service,
    get_chat_service,
    get_evaluation_service,
    get_router_agent,
    get_task_service,
    get_workflow_service,
)
from app.schemas import ChatRequest, ChatResponse, CreateApprovalRequest
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService
from app.services.evaluation_service import EvaluationService
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    router_agent: RouterAgent = Depends(get_router_agent),
    audit_service: AuditService = Depends(get_audit_service),
    approval_service: ApprovalService = Depends(get_approval_service),
    chat_service: ChatService = Depends(get_chat_service),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    task_service: TaskService = Depends(get_task_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ChatResponse:
    route_plan = router_agent.plan(request)
    selected_capability_id = route_plan.selected.capability_id
    capability_name = route_plan.selected.capability_name
    runtime_task = task_service.create_runtime_task(
        request=request,
        selected_agent_id=selected_capability_id,
        capability_name=capability_name,
    )
    request.metadata["_runtime_context"] = {
        **runtime_task,
        "emit_event": task_service.emit_runtime_event,
    }
    response = router_agent.run(request)
    response.task_id = runtime_task["task_id"]

    workflow_service.emit_workflow_events(
        task_id=response.task_id,
        contact_id=runtime_task["contact_id"],
        request=request,
        response=response,
        emit_event=task_service.emit_runtime_event,
    )
    if response.workflow:
        response.audit_tags.append(f"workflow:{response.workflow}")

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
                    "task_id": response.task_id,
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
            "workflow": response.workflow,
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
    contact_id = task_service.finalize_chat_task(
        task_id=response.task_id,
        response=response,
        approval_id=response.approval_id,
    )
    response.evaluation_id = evaluation_service.evaluate_chat_result(
        task_id=response.task_id,
        contact_id=contact_id,
        request=request,
        response=response,
    )

    return response
