from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas import (
    AgentEvaluationAnalyticsItemResponse,
    AgentEvaluationDetailResponse,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
    AgentOptimizationSuggestionResponse,
    AgentObservationLogResponse,
    ChatRequest,
    ChatResponse,
    DataAccessLogResponse,
    ToolCallLogResponse,
)
from app.services.observation_service import ObservationService
from app.services.tool_execution_log_service import ToolExecutionLogService


@dataclass(frozen=True)
class EvaluationRuntimeFacts:
    observations: list[AgentObservationLogResponse]
    tool_calls: list[ToolCallLogResponse]
    data_access_logs: list[DataAccessLogResponse]
    fallback_count: int
    total_latency_ms: int
    sensitive_access_count: int
    approved_access_count: int
    planner_observed: bool
    executor_observed: bool


class EvaluationService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: EvaluationRepository,
        observation_service: ObservationService | None = None,
        tool_execution_log_service: ToolExecutionLogService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository
        self._observation_service = observation_service
        self._tool_execution_log_service = tool_execution_log_service

    def evaluate_chat_result(
        self,
        *,
        task_id: str,
        contact_id: str | None,
        request: ChatRequest,
        response: ChatResponse,
    ) -> str:
        runtime_facts = self._collect_runtime_facts(task_id=task_id)
        scores = self._build_scores(
            request=request,
            response=response,
            runtime_facts=runtime_facts,
        )
        summary = self._build_summary(
            response=response,
            overall_score=scores["overall"],
            runtime_facts=runtime_facts,
        )
        details = self._build_details(
            response=response,
            scores=scores,
            runtime_facts=runtime_facts,
        )
        suggestions = self._build_suggestions(
            response=response,
            scores=scores,
            runtime_facts=runtime_facts,
        )

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

    def _collect_runtime_facts(self, *, task_id: str) -> EvaluationRuntimeFacts:
        observations = (
            self._observation_service.list_observations(task_id=task_id)
            if self._observation_service is not None
            else []
        )
        tool_calls = (
            self._tool_execution_log_service.list_tool_call_logs(task_id=task_id)
            if self._tool_execution_log_service is not None
            else []
        )
        data_access_logs = (
            self._tool_execution_log_service.list_data_access_logs(task_id=task_id)
            if self._tool_execution_log_service is not None
            else []
        )
        fallback_count = sum(1 for item in observations if item.fallback_used)
        total_latency_ms = sum(item.latency_ms or 0 for item in observations)
        sensitive_access_count = sum(
            1 for item in data_access_logs if item.sensitive_level in {"high", "medium"}
        )
        approved_access_count = sum(1 for item in data_access_logs if item.approved)
        phase_set = {item.phase for item in observations if item.phase}
        return EvaluationRuntimeFacts(
            observations=observations,
            tool_calls=tool_calls,
            data_access_logs=data_access_logs,
            fallback_count=fallback_count,
            total_latency_ms=total_latency_ms,
            sensitive_access_count=sensitive_access_count,
            approved_access_count=approved_access_count,
            planner_observed="planner" in phase_set,
            executor_observed="executor" in phase_set,
        )

    def list_evaluations(self) -> list[AgentEvaluationSummaryResponse]:
        with self._session_factory() as session:
            return [self._to_summary(item) for item in self._repository.list_evaluations(session)]

    def summarize_by_agent(self) -> list[AgentEvaluationAnalyticsItemResponse]:
        evaluations = self.list_evaluations()
        grouped: dict[str, list[AgentEvaluationSummaryResponse]] = {}
        for item in evaluations:
            grouped.setdefault(item.agent_id, []).append(item)

        result: list[AgentEvaluationAnalyticsItemResponse] = []
        for agent_id, items in grouped.items():
            total = len(items)
            result.append(
                AgentEvaluationAnalyticsItemResponse(
                    agent_id=agent_id,
                    evaluation_count=total,
                    excellent_count=sum(1 for item in items if item.result_label == "excellent"),
                    good_count=sum(1 for item in items if item.result_label == "good"),
                    poor_count=sum(1 for item in items if item.result_label == "poor"),
                    average_overall_score=round(
                        sum(item.overall_score for item in items) / total,
                        2,
                    ),
                    average_efficiency_score=round(
                        sum(item.efficiency_score for item in items) / total,
                        2,
                    ),
                    average_tool_usage_score=round(
                        sum(item.tool_usage_score for item in items) / total,
                        2,
                    ),
                )
            )
        return sorted(result, key=lambda item: item.average_overall_score, reverse=True)

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
    def _build_scores(
        *,
        request: ChatRequest,
        response: ChatResponse,
        runtime_facts: EvaluationRuntimeFacts,
    ) -> dict[str, float]:
        completion = 95.0 if response.summary else 40.0
        if runtime_facts.planner_observed and runtime_facts.executor_observed:
            completion = min(98.0, completion + 2.0)

        accuracy = 90.0 if response.references else 80.0
        if runtime_facts.tool_calls:
            accuracy = min(95.0, accuracy + 2.0)

        selected_tool_count = len(response.selected_tools)
        executed_tool_count = len(runtime_facts.tool_calls)
        if selected_tool_count == 0:
            tool_usage = 80.0 if executed_tool_count == 0 else 74.0
        elif executed_tool_count >= selected_tool_count:
            tool_usage = 93.0
        elif executed_tool_count > 0:
            tool_usage = 84.0
        else:
            tool_usage = 70.0

        efficiency = 88.0 if selected_tool_count <= 2 else 78.0
        if runtime_facts.total_latency_ms >= 1500:
            efficiency -= 8.0
        elif runtime_facts.total_latency_ms >= 500:
            efficiency -= 4.0
        if runtime_facts.fallback_count > 0:
            efficiency -= min(8.0, runtime_facts.fallback_count * 3.0)
        efficiency = max(55.0, efficiency)

        compliance = 88.0 if not response.requires_approval else 82.0
        if runtime_facts.sensitive_access_count > runtime_facts.approved_access_count:
            compliance -= 10.0
        if runtime_facts.data_access_logs and runtime_facts.approved_access_count == len(
            runtime_facts.data_access_logs
        ):
            compliance += 2.0
        compliance = max(60.0, min(95.0, compliance))

        user_feedback = 75.0
        cost = 86.0 if len(request.message) < 200 else 78.0
        if executed_tool_count >= 3:
            cost -= 6.0
        elif executed_tool_count == 2:
            cost -= 2.0
        if runtime_facts.total_latency_ms >= 1500:
            cost -= 4.0
        cost = max(68.0, cost)

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
    def _build_summary(
        *,
        response: ChatResponse,
        overall_score: float,
        runtime_facts: EvaluationRuntimeFacts,
    ) -> str:
        return (
            f"评估 Agent 认为当前任务总体表现为 {overall_score:.2f} 分，"
            f"主要由 {response.capability_name} 完成。"
            f"本次观测到 {len(runtime_facts.observations)} 条运行观测、"
            f"{len(runtime_facts.tool_calls)} 次工具调用，"
            f"fallback {runtime_facts.fallback_count} 次，"
            f"可用于后续路由优化、提示词优化和工具编排调整。"
        )

    @staticmethod
    def _build_details(
        *,
        response: ChatResponse,
        scores: dict[str, float],
        runtime_facts: EvaluationRuntimeFacts,
    ) -> list[dict]:
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
                "evidence": (
                    f"selected={','.join(response.selected_tools) or 'none'};"
                    f" executed={len(runtime_facts.tool_calls)}"
                ),
                "suggestion": "保持工具选择收敛，减少低收益调用，提升执行稳定性。",
            },
            {
                "dimension_code": "efficiency",
                "dimension_name": "执行效率",
                "score": scores["efficiency"],
                "evidence": (
                    f"latency_ms={runtime_facts.total_latency_ms};"
                    f" fallback_count={runtime_facts.fallback_count}"
                ),
                "suggestion": "持续降低 fallback 频率和总执行耗时，提升稳定性与实时性。",
            },
            {
                "dimension_code": "compliance",
                "dimension_name": "合规与风险控制",
                "score": scores["compliance"],
                "evidence": (
                    f"requires_approval={response.requires_approval};"
                    f" sensitive_access={runtime_facts.sensitive_access_count};"
                    f" approved_access={runtime_facts.approved_access_count}"
                ),
                "suggestion": "高风险场景继续绑定审批、审计和数据访问留痕策略。",
            },
        ]

    @staticmethod
    def _build_suggestions(
        *,
        response: ChatResponse,
        scores: dict[str, float],
        runtime_facts: EvaluationRuntimeFacts,
    ) -> list[dict]:
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
        if runtime_facts.fallback_count > 0:
            suggestions.append(
                {
                    "optimization_type": "runtime",
                    "target_ref": response.capability_id,
                    "current_value_summary": (
                        f"fallback_count={runtime_facts.fallback_count}, "
                        f"observations={len(runtime_facts.observations)}"
                    ),
                    "suggested_change": "补齐 AgentScope 模型桥接配置或增强 runtime session 编排，降低本地 fallback 比例。",
                    "priority": "high",
                }
            )
        if scores["efficiency"] < 80:
            suggestions.append(
                {
                    "optimization_type": "workflow",
                    "target_ref": response.workflow or response.capability_id,
                    "current_value_summary": f"total_latency_ms={runtime_facts.total_latency_ms}",
                    "suggested_change": "优化 planner 到 executor 的链路，收敛工具数和中间阶段，缩短端到端耗时。",
                    "priority": "medium",
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
