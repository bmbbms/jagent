from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_evaluation_service
from app.schemas import AgentEvaluationResponse, AgentEvaluationSummaryResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("", response_model=list[AgentEvaluationSummaryResponse])
def list_evaluations(
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[AgentEvaluationSummaryResponse]:
    return evaluation_service.list_evaluations()


@router.get("/{evaluation_id}", response_model=AgentEvaluationResponse)
def get_evaluation(
    evaluation_id: str,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> AgentEvaluationResponse:
    item = evaluation_service.get_evaluation(evaluation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return item
