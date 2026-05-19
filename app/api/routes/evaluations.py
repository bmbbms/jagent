from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_evaluation_service
from app.schemas import (
    AgentEvaluationAnalyticsOverviewResponse,
    AgentEvaluationAnalyticsItemResponse,
    AgentOptimizationSuggestionOverviewResponse,
    AgentOptimizationSuggestionResponse,
    AgentOptimizationSuggestionUpdateRequest,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("", response_model=list[AgentEvaluationSummaryResponse])
def list_evaluations(
    agent_id: str | None = Query(default=None),
    result_label: str | None = Query(default=None),
    min_overall_score: float | None = Query(default=None, ge=0, le=100),
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    attention_level: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationSummaryResponse]:
    create_time_from = (
        datetime.combine(start_date_from, time.min) if start_date_from is not None else None
    )
    create_time_to = (
        datetime.combine(start_date_to, time.max) if start_date_to is not None else None
    )
    return evaluation_service.filter_evaluations(
        agent_id=agent_id,
        result_label=result_label,
        min_overall_score=min_overall_score,
        create_time_from=create_time_from,
        create_time_to=create_time_to,
        attention_level=attention_level,
    )


@router.get("/analytics/by-agent", response_model=list[AgentEvaluationAnalyticsItemResponse])
def list_evaluation_analytics_by_agent(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationAnalyticsItemResponse]:
    return evaluation_service.summarize_by_agent()


@router.get("/analytics/overview", response_model=AgentEvaluationAnalyticsOverviewResponse)
def get_evaluation_analytics_overview(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationAnalyticsOverviewResponse:
    return evaluation_service.build_analytics_overview()


@router.get(
    "/suggestions",
    response_model=list[AgentOptimizationSuggestionResponse],
)
def list_optimization_suggestions(
    agent_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentOptimizationSuggestionResponse]:
    return evaluation_service.list_optimization_suggestions(
        agent_id=agent_id,
        status=status,
        owner=owner,
    )


@router.get(
    "/suggestions/overview",
    response_model=AgentOptimizationSuggestionOverviewResponse,
)
def get_optimization_suggestion_overview(
    agent_id: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentOptimizationSuggestionOverviewResponse:
    return evaluation_service.build_optimization_suggestion_overview(
        agent_id=agent_id,
        owner=owner,
    )


@router.put(
    "/suggestions/{suggestion_id}",
    response_model=AgentOptimizationSuggestionResponse,
)
def update_optimization_suggestion(
    suggestion_id: int,
    request: AgentOptimizationSuggestionUpdateRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentOptimizationSuggestionResponse:
    item = evaluation_service.update_optimization_suggestion(suggestion_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="optimization suggestion not found")
    return item


@router.get("/{evaluation_id}", response_model=AgentEvaluationResponse)
def get_evaluation(
    evaluation_id: str,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationResponse:
    item = evaluation_service.get_evaluation(evaluation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return item
