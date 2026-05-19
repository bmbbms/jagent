from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_audit_service, get_evaluation_service
from app.schemas import (
    AgentEvaluationAnalyticsOverviewResponse,
    AgentEvaluationDimensionAnalyticsResponse,
    AgentEvaluationAnalyticsItemResponse,
    AgentEvaluationFocusAgentResponse,
    AgentEvaluationRootCauseAnalyticsResponse,
    AgentEvaluationTrendResponse,
    AgentOptimizationSuggestionOverviewResponse,
    AgentOptimizationSuggestionResponse,
    AgentOptimizationSuggestionTicketRequest,
    AgentOptimizationSuggestionUpdateRequest,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
)
from app.services.audit_service import AuditService
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


@router.get("/analytics/focus-agents", response_model=list[AgentEvaluationFocusAgentResponse])
def list_evaluation_focus_agents(
    limit: int = Query(default=10, ge=1, le=50),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationFocusAgentResponse]:
    return evaluation_service.list_focus_agents(limit=limit)


@router.get(
    "/analytics/dimensions",
    response_model=list[AgentEvaluationDimensionAnalyticsResponse],
)
def list_evaluation_dimension_analytics(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationDimensionAnalyticsResponse]:
    return evaluation_service.summarize_dimensions()


@router.get(
    "/analytics/root-causes",
    response_model=list[AgentEvaluationRootCauseAnalyticsResponse],
)
def list_evaluation_root_cause_analytics(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationRootCauseAnalyticsResponse]:
    return evaluation_service.summarize_root_causes()


@router.get("/analytics/trend", response_model=AgentEvaluationTrendResponse)
def get_evaluation_analytics_trend(
    agent_id: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationTrendResponse:
    return evaluation_service.build_evaluation_trend(agent_id=agent_id, limit=limit)


@router.get(
    "/suggestions",
    response_model=list[AgentOptimizationSuggestionResponse],
)
def list_optimization_suggestions(
    agent_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentOptimizationSuggestionResponse]:
    return evaluation_service.list_optimization_suggestions(
        agent_id=agent_id,
        status=status,
        owner=owner,
        priority=priority,
    )


@router.get(
    "/suggestions/overview",
    response_model=AgentOptimizationSuggestionOverviewResponse,
)
def get_optimization_suggestion_overview(
    agent_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentOptimizationSuggestionOverviewResponse:
    return evaluation_service.build_optimization_suggestion_overview(
        agent_id=agent_id,
        status=status,
        owner=owner,
        priority=priority,
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


@router.post(
    "/suggestions/{suggestion_id}/ticket",
    response_model=AgentOptimizationSuggestionResponse,
)
def create_optimization_suggestion_ticket(
    suggestion_id: int,
    request: AgentOptimizationSuggestionTicketRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AgentOptimizationSuggestionResponse:
    suggestion_ctx = evaluation_service.get_suggestion_audit_context(suggestion_id)
    item = evaluation_service.create_suggestion_ticket(suggestion_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="optimization suggestion not found")
    audit_service.record(
        "service_ticket.create",
        request.requested_by,
        {
            "source": "evaluation",
            "event_type": "service_ticket",
            "task_id": suggestion_ctx.get("task_id") if suggestion_ctx else None,
            "evaluation_id": suggestion_ctx.get("evaluation_id") if suggestion_ctx else None,
            "suggestion_id": item.suggestion_id,
            "ticket_id": item.ticket_id,
            "ticket_status": item.ticket_status,
            "agent_id": suggestion_ctx.get("agent_id") if suggestion_ctx else None,
            "capability_id": suggestion_ctx.get("agent_id") if suggestion_ctx else None,
            "request_summary": "create service ticket from optimization suggestion",
            "response_summary": item.suggested_change,
            "outcome": 1,
            "payload": {
                "ticket_id": item.ticket_id,
                "suggestion_id": item.suggestion_id,
                "evaluation_id": suggestion_ctx.get("evaluation_id") if suggestion_ctx else None,
                "task_id": suggestion_ctx.get("task_id") if suggestion_ctx else None,
                "priority": item.priority,
                "owner": item.owner,
            },
        },
    )
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
