from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas import (
    AgentEvaluationDetailResponse,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
    AgentOptimizationSuggestionResponse,
    ChatRequest,
    ChatResponse,
)


class EvaluationService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: EvaluationRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def evaluate_chat_result(
        self,
        *,
        task_id: str,
        contact_id: str | None,
        request: ChatRequest,
        response: ChatResponse,
    ) -> str:
        scores = self._build_scores(request=request, response=response)
        summary = self._build_summary(response=response, overall_score=scores["overall"])
        details = self._build_details(response=response, scores=scores)
        suggestions = self._build_suggestions(response=response, scores=scores)

        with session_scope(self._session_factory) as session:
            item = self._repository.create_evaluation(
                session,
                task_id=task_id,
                contact_id=contact_id,
                agent_id=response.capability_id,
                evaluator_agent_id="evaluation.agent",
                evaluation_mode="online",
                overall_score=scores["overall"],
                completion_score=scores["completion"],
                accuracy_score=scores["accuracy"],
                tool_usage_score=scores["tool_usage"],
                efficiency_score=scores["efficiency"],
                compliance_score=scores["compliance"],
                user_feedback_score=scores["user_feedback"],
                cost_score=scores["cost"],
                result_label=self._score_label(scores["overall"]),
                summary=summary,
            )
            self._repository.add_details(
                session,
                evaluation_id=item.evaluation_id,
                details=details,
            )
            self._repository.add_suggestions(
                session,
                evaluation_id=item.evaluation_id,
                agent_id=response.capability_id,
                suggestions=suggestions,
            )
            return item.evaluation_id

    def list_evaluations(self) -> list[AgentEvaluationSummaryResponse]:
        with self._session_factory() as session:
            return [self._to_summary(item) for item in self._repository.list_evaluations(session)]

    def get_evaluation(self, evaluation_id: str) -> AgentEvaluationResponse | None:
        with self._session_factory() as session:
            item = self._repository.get_evaluation(session, evaluation_id)
            if item is None:
                return None
            return self._build_evaluation_response(
                session=session,
                evaluation_id=item.evaluation_id,
                item=item,
            )

    def get_latest_by_task(self, task_id: str) -> AgentEvaluationResponse | None:
        with self._session_factory() as session:
            item = self._repository.get_latest_by_task(session, task_id)
            if item is None:
                return None
            return self._build_evaluation_response(
                session=session,
                evaluation_id=item.evaluation_id,
                item=item,
            )

    def _build_evaluation_response(
        self,
        *,
        session: Session,
        evaluation_id: str,
        item,
    ) -> AgentEvaluationResponse:
        details = [self._to_detail(x) for x in self._repository.list_details(session, evaluation_id)]
        suggestions = [
            self._to_suggestion(x)
            for x in self._repository.list_suggestions(session, evaluation_id)
        ]
        payload = self._to_summary(item).model_dump()
        payload["details"] = [x.model_dump() for x in details]
        payload["suggestions"] = [x.model_dump() for x in suggestions]
        return AgentEvaluationResponse(**payload)

    @staticmethod
    def _build_scores(*, request: ChatRequest, response: ChatResponse) -> dict[str, float]:
        completion = 95.0 if response.summary else 40.0
        accuracy = 90.0 if response.references else 80.0
        tool_usage = 92.0 if response.selected_tools else 75.0
        efficiency = 85.0 if len(response.selected_tools) <= 2 else 72.0
        compliance = 88.0 if not response.requires_approval else 80.0
        user_feedback = 75.0
        cost = 86.0 if len(request.message) < 200 else 78.0
        overall = round(
            (
                completion
                + accuracy
                + tool_usage
                + efficiency
                + compliance
                + user_feedback
                + cost
            )
            / 7,
            2,
        )
        return {
            "overall": overall,
            "completion": completion,
            "accuracy": accuracy,
            "tool_usage": tool_usage,
            "efficiency": efficiency,
            "compliance": compliance,
            "user_feedback": user_feedback,
            "cost": cost,
        }

    @staticmethod
    def _build_summary(*, response: ChatResponse, overall_score: float) -> str:
        return (
            f"评估 Agent 认为当前任务总体表现为 {overall_score:.2f} 分，"
            f"主要由 {response.capability_name} 完成，可用于后续路由优化、提示词优化和工具编排调整。"
        )

    @staticmethod
    def _build_details(*, response: ChatResponse, scores: dict[str, float]) -> list[dict]:
        return [
            {
                "dimension_code": "completion",
                "dimension_name": "任务完成度",
                "score": scores["completion"],
                "evidence": response.summary,
                "suggestion": "继续补强结果结构化输出，让任务结论更容易复核和回放。",
            },
            {
                "dimension_code": "tool_usage",
                "dimension_name": "工具使用合理性",
                "score": scores["tool_usage"],
                "evidence": ",".join(response.selected_tools) or "未使用工具",
                "suggestion": "保持工具选择收敛，减少低收益调用，提升执行稳定性。",
            },
            {
                "dimension_code": "compliance",
                "dimension_name": "合规与风险控制",
                "score": scores["compliance"],
                "evidence": f"requires_approval={response.requires_approval}",
                "suggestion": "高风险场景继续绑定审批、审计和数据访问留痕策略。",
            },
        ]

    @staticmethod
    def _build_suggestions(*, response: ChatResponse, scores: dict[str, float]) -> list[dict]:
        suggestions = [
            {
                "optimization_type": "prompt",
                "target_ref": response.capability_id,
                "current_value_summary": response.summary[:200],
                "suggested_change": "增加任务目标、输出格式和边界条件描述，提升回复稳定性与一致性。",
                "priority": "medium",
            }
        ]
        if scores["tool_usage"] < 85:
            suggestions.append(
                {
                    "optimization_type": "tool",
                    "target_ref": response.capability_id,
                    "current_value_summary": ",".join(response.selected_tools),
                    "suggested_change": "收敛工具清单，仅保留高命中率工具，并增加工具选择规则。",
                    "priority": "high",
                }
            )
        return suggestions

    @staticmethod
    def _score_label(score: float) -> str:
        if score >= 90:
            return "excellent"
        if score >= 75:
            return "good"
        return "poor"

    @staticmethod
    def _to_summary(item) -> AgentEvaluationSummaryResponse:
        return AgentEvaluationSummaryResponse(
            evaluation_id=item.evaluation_id,
            task_id=item.task_id,
            agent_id=item.agent_id,
            evaluator_agent_id=item.evaluator_agent_id,
            evaluation_mode=item.evaluation_mode,
            overall_score=item.overall_score,
            completion_score=item.completion_score,
            accuracy_score=item.accuracy_score,
            tool_usage_score=item.tool_usage_score,
            efficiency_score=item.efficiency_score,
            compliance_score=item.compliance_score,
            user_feedback_score=item.user_feedback_score,
            cost_score=item.cost_score,
            result_label=item.result_label,
            summary=item.summary or "",
            create_time=item.create_time.isoformat(),
        )

    @staticmethod
    def _to_detail(item) -> AgentEvaluationDetailResponse:
        return AgentEvaluationDetailResponse(
            dimension_code=item.dimension_code,
            dimension_name=item.dimension_name,
            score=item.score,
            problem_type=item.problem_type,
            evidence=item.evidence or "",
            suggestion=item.suggestion or "",
            severity=item.severity,
        )

    @staticmethod
    def _to_suggestion(item) -> AgentOptimizationSuggestionResponse:
        return AgentOptimizationSuggestionResponse(
            optimization_type=item.optimization_type,
            target_ref=item.target_ref,
            current_value_summary=item.current_value_summary or "",
            suggested_change=item.suggested_change,
            priority=item.priority,
            status=item.status,
            owner=item.owner,
        )
