from fastapi import APIRouter, Depends, HTTPException

from app.schemas import BizDomain, WorkflowDefinitionResponse
from app.services.workflow_service import WorkflowService
from app.dependencies import get_workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowDefinitionResponse])
def list_workflows(
    biz_domain: BizDomain | None = None,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowDefinitionResponse]:
    return workflow_service.list_workflows(biz_domain)


@router.get("/{workflow_code}", response_model=WorkflowDefinitionResponse)
def get_workflow(
    workflow_code: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDefinitionResponse:
    item = workflow_service.get_workflow(workflow_code)
    if item is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return item
