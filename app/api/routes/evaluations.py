from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_evaluation_service
from app.schemas import (
    AgentEvaluationAnalyticsItemResponse,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("", response_model=list[AgentEvaluationSummaryResponse])
def list_evaluations(
    agent_id: str | None = Query(default=None),
    result_label: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationSummaryResponse]:
    items = evaluation_service.list_evaluations()
    if agent_id:
        items = [item for item in items if item.agent_id == agent_id]
    if result_label:
        items = [item for item in items if item.result_label == result_label]
    return items


@router.get("/analytics/by-agent", response_model=list[AgentEvaluationAnalyticsItemResponse])
def list_evaluation_analytics_by_agent(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationAnalyticsItemResponse]:
    return evaluation_service.summarize_by_agent()


@router.get("/{evaluation_id}", response_model=AgentEvaluationResponse)
def get_evaluation(
    evaluation_id: str,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationResponse:
    item = evaluation_service.get_evaluation(evaluation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return item
