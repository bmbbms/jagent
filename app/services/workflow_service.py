from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from app.schemas import (
    BizDomain,
    ChatRequest,
    ChatResponse,
    WorkflowDefinitionResponse,
    WorkflowStepResponse,
)
from app.workflows import WorkflowDefinition, WorkflowRegistry


class WorkflowService:
    def __init__(self, registry: WorkflowRegistry) -> None:
        self._registry = registry

    def list_workflows(
        self,
        biz_domain: BizDomain | None = None,
        workflow_code: str | None = None,
        required_tool: str | None = None,
        has_approval_points: bool | None = None,
    ) -> list[WorkflowDefinitionResponse]:
        items = self._registry.list(biz_domain)
        if workflow_code:
            items = [item for item in items if item.workflow_code == workflow_code]
        if required_tool:
            items = [item for item in items if required_tool in item.required_tools]
        if has_approval_points is not None:
            items = [
                item
                for item in items
                if bool(item.approval_points) == has_approval_points
            ]
        return [self._to_response(item) for item in items]

    def get_workflow(self, workflow_code: str) -> WorkflowDefinitionResponse | None:
        item = self._registry.get(workflow_code)
        if item is None:
            return None
        return self._to_response(item)

    def emit_workflow_events(
        self,
        *,
        task_id: str,
        contact_id: str,
        request: ChatRequest,
        response: ChatResponse,
        emit_event: Callable[..., dict[str, Any] | None] | None,
    ) -> WorkflowDefinitionResponse | None:
        workflow_code = response.workflow
        if not workflow_code:
            return None
        workflow = self._registry.get(workflow_code)
        if workflow is None or emit_event is None or not task_id:
            return self._to_response(workflow) if workflow else None

        emit_event(
            task_id=task_id,
            event_type="workflow_started",
            title="Workflow 已启动",
            content=workflow.name,
            agent_id=response.capability_id,
            current_stage="workflow",
            task_status="running",
            event_payload={
                "workflow": self._serialize_workflow(workflow),
                "contact_id": contact_id,
                "message": request.message,
            },
        )

        for index, step in enumerate(workflow.steps, start=1):
            emit_event(
                task_id=task_id,
                event_type="workflow_step_registered",
                title=f"Workflow 步骤 {index}",
                content=step.name,
                agent_id=response.capability_id,
                current_stage="workflow",
                event_payload={
                    "workflow_code": workflow.workflow_code,
                    "workflow_name": workflow.name,
                    "step_index": index,
                    "step": asdict(step),
                },
            )

        if workflow.approval_points:
            emit_event(
                task_id=task_id,
                event_type="workflow_approval_checkpoint",
                title="Workflow 审批检查点",
                content=" / ".join(workflow.approval_points),
                agent_id=response.capability_id,
                current_stage="workflow",
                event_payload={
                    "workflow_code": workflow.workflow_code,
                    "approval_points": workflow.approval_points,
                    "requires_approval": response.requires_approval,
                },
            )

        return self._to_response(workflow)

    def _to_response(self, workflow: WorkflowDefinition) -> WorkflowDefinitionResponse:
        return WorkflowDefinitionResponse(
            workflow_code=workflow.workflow_code,
            name=workflow.name,
            biz_domain=workflow.biz_domain,
            purpose=workflow.purpose,
            required_inputs=list(workflow.required_inputs),
            required_tools=list(workflow.required_tools),
            approval_points=list(workflow.approval_points),
            fallback_rules=list(workflow.fallback_rules),
            audit_tags=list(workflow.audit_tags),
            steps=[
                WorkflowStepResponse(
                    step_code=item.step_code,
                    name=item.name,
                    step_type=item.step_type,
                    description=item.description,
                    required_tools=list(item.required_tools),
                    approval_required=item.approval_required,
                )
                for item in workflow.steps
            ],
        )

    def _serialize_workflow(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        return {
            "workflow_code": workflow.workflow_code,
            "name": workflow.name,
            "biz_domain": workflow.biz_domain.value,
            "purpose": workflow.purpose,
            "required_inputs": workflow.required_inputs,
            "required_tools": workflow.required_tools,
            "approval_points": workflow.approval_points,
            "fallback_rules": workflow.fallback_rules,
            "audit_tags": workflow.audit_tags,
            "steps": [asdict(item) for item in workflow.steps],
        }
