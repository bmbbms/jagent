from __future__ import annotations

from typing import Iterable, List
from uuid import uuid4

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
        for detail in details:
            session.add(
                AgentEvaluationDetailModel(
                    id=self._new_numeric_id(),
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
        session.flush()

    def add_suggestions(
        self,
        session: Session,
        *,
        evaluation_id: str,
        agent_id: str,
        suggestions: Iterable[dict],
    ) -> None:
        for suggestion in suggestions:
            session.add(
                AgentOptimizationSuggestionModel(
                    id=self._new_numeric_id(),
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

    def list_all_suggestions(
        self,
        session: Session,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        owner: str | None = None,
    ) -> List[AgentOptimizationSuggestionModel]:
        query = session.query(AgentOptimizationSuggestionModel).order_by(
            AgentOptimizationSuggestionModel.create_time.desc(),
            AgentOptimizationSuggestionModel.id.desc(),
        )
        if agent_id:
            query = query.filter(AgentOptimizationSuggestionModel.agent_id == agent_id)
        if status:
            query = query.filter(AgentOptimizationSuggestionModel.status == status)
        if owner:
            query = query.filter(AgentOptimizationSuggestionModel.owner == owner)
        return query.all()

    def get_suggestion(
        self,
        session: Session,
        suggestion_id: int,
    ) -> AgentOptimizationSuggestionModel | None:
        return session.get(AgentOptimizationSuggestionModel, suggestion_id)

    def update_suggestion(
        self,
        session: Session,
        *,
        suggestion_id: int,
        status: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
    ) -> AgentOptimizationSuggestionModel | None:
        item = session.get(AgentOptimizationSuggestionModel, suggestion_id)
        if item is None:
            return None
        if status is not None:
            item.status = status
        if owner is not None:
            item.owner = owner
        if priority is not None:
            item.priority = priority
        session.flush()
        return item

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:24]}"

    @staticmethod
    def _new_numeric_id() -> int:
        return uuid4().int & ((1 << 63) - 1)
