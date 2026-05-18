from __future__ import annotations

from typing import Iterable, List
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AgentEvaluationDetailModel,
    AgentEvaluationModel,
    AgentOptimizationSuggestionModel,
)


class EvaluationRepository:
    def create_evaluation(
        self,
        session: Session,
        *,
        task_id: str,
        contact_id: str | None,
        agent_id: str,
        evaluator_agent_id: str,
        evaluation_mode: str,
        overall_score: float,
        completion_score: float,
        accuracy_score: float,
        tool_usage_score: float,
        efficiency_score: float,
        compliance_score: float,
        user_feedback_score: float,
        cost_score: float,
        result_label: str,
        summary: str,
    ) -> AgentEvaluationModel:
        item = AgentEvaluationModel(
            evaluation_id=self._new_id("eval"),
            task_id=task_id,
            contact_id=contact_id,
            agent_id=agent_id,
            evaluator_agent_id=evaluator_agent_id,
            evaluation_mode=evaluation_mode,
            overall_score=overall_score,
            completion_score=completion_score,
            accuracy_score=accuracy_score,
            tool_usage_score=tool_usage_score,
            efficiency_score=efficiency_score,
            compliance_score=compliance_score,
            user_feedback_score=user_feedback_score,
            cost_score=cost_score,
            result_label=result_label,
            summary=summary,
        )
        session.add(item)
        session.flush()
        return item

    def add_details(
        self,
        session: Session,
        *,
        evaluation_id: str,
        details: Iterable[dict],
    ) -> None:
        next_id = (
            session.query(func.max(AgentEvaluationDetailModel.id)).scalar() or 0
        ) + 1
        for detail in details:
            session.add(
                AgentEvaluationDetailModel(
                    id=next_id,
                    evaluation_id=evaluation_id,
                    dimension_code=detail["dimension_code"],
                    dimension_name=detail["dimension_name"],
                    score=detail["score"],
                    problem_type=detail.get("problem_type"),
                    evidence=detail.get("evidence"),
                    suggestion=detail.get("suggestion"),
                    severity=detail.get("severity"),
                )
            )
            next_id += 1
        session.flush()

    def add_suggestions(
        self,
        session: Session,
        *,
        evaluation_id: str,
        agent_id: str,
        suggestions: Iterable[dict],
    ) -> None:
        next_id = (
            session.query(func.max(AgentOptimizationSuggestionModel.id)).scalar() or 0
        ) + 1
        for suggestion in suggestions:
            session.add(
                AgentOptimizationSuggestionModel(
                    id=next_id,
                    evaluation_id=evaluation_id,
                    agent_id=agent_id,
                    optimization_type=suggestion["optimization_type"],
                    target_ref=suggestion.get("target_ref"),
                    current_value_summary=suggestion.get("current_value_summary"),
                    suggested_change=suggestion["suggested_change"],
                    priority=suggestion.get("priority", "medium"),
                    status=suggestion.get("status", "new"),
                    owner=suggestion.get("owner"),
                )
            )
            next_id += 1
        session.flush()

    def list_evaluations(self, session: Session, limit: int = 50) -> List[AgentEvaluationModel]:
        return (
            session.query(AgentEvaluationModel)
            .order_by(AgentEvaluationModel.create_time.desc())
            .limit(limit)
            .all()
        )

    def get_evaluation(self, session: Session, evaluation_id: str) -> AgentEvaluationModel | None:
        return session.get(AgentEvaluationModel, evaluation_id)

    def get_latest_by_task(
        self,
        session: Session,
        task_id: str,
    ) -> AgentEvaluationModel | None:
        return (
            session.query(AgentEvaluationModel)
            .filter(AgentEvaluationModel.task_id == task_id)
            .order_by(AgentEvaluationModel.create_time.desc())
            .first()
        )

    def list_details(
        self, session: Session, evaluation_id: str
    ) -> List[AgentEvaluationDetailModel]:
        return (
            session.query(AgentEvaluationDetailModel)
            .filter(AgentEvaluationDetailModel.evaluation_id == evaluation_id)
            .all()
        )

    def list_suggestions(
        self, session: Session, evaluation_id: str
    ) -> List[AgentOptimizationSuggestionModel]:
        return (
            session.query(AgentOptimizationSuggestionModel)
            .filter(AgentOptimizationSuggestionModel.evaluation_id == evaluation_id)
            .order_by(AgentOptimizationSuggestionModel.create_time.asc())
            .all()
        )

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:24]}"
