from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ServiceTicketModel
from app.db.session import session_scope
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas import (
    AgentEvaluationDimensionAnalyticsResponse,
    AgentEvaluationAnalyticsItemResponse,
    AgentEvaluationAnalyticsOverviewResponse,
    AgentEvaluationFocusAgentResponse,
    AgentEvaluationDetailResponse,
    AgentEvaluationRootCauseAnalyticsResponse,
    AgentEvaluationResponse,
    AgentEvaluationSummaryResponse,
    AgentEvaluationTrendPointResponse,
    AgentEvaluationTrendResponse,
    AgentObservationLogResponse,
    AgentOptimizationSuggestionOverviewResponse,
    AgentOptimizationExecutionBacklogItemResponse,
    AgentOptimizationExecutionBacklogResponse,
    AgentOptimizationExecutionPlanItemResponse,
    AgentOptimizationExecutionPlanResponse,
    AgentOptimizationSuggestionResponse,
    AgentOptimizationSuggestionTicketRequest,
    AgentOptimizationSuggestionUpdateRequest,
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

    def list_evaluations(self) -> list[AgentEvaluationSummaryResponse]:
        with self._session_factory() as session:
            return [self._to_summary(item) for item in self._repository.list_evaluations(session)]

    def filter_evaluations(
        self,
        *,
        agent_id: str | None = None,
        result_label: str | None = None,
        min_overall_score: float | None = None,
        create_time_from: datetime | None = None,
        create_time_to: datetime | None = None,
        attention_level: str | None = None,
    ) -> list[AgentEvaluationSummaryResponse]:
        items = self.list_evaluations()
        if agent_id:
            items = [item for item in items if item.agent_id == agent_id]
        if result_label:
            items = [item for item in items if item.result_label == result_label]
        if min_overall_score is not None:
            items = [item for item in items if item.overall_score >= min_overall_score]
        if create_time_from is not None:
            items = [
                item
                for item in items
                if datetime.fromisoformat(item.create_time) >= create_time_from
            ]
        if create_time_to is not None:
            items = [
                item
                for item in items
                if datetime.fromisoformat(item.create_time) <= create_time_to
            ]
        if attention_level:
            analytics_by_agent = {item.agent_id: item for item in self.summarize_by_agent()}
            items = [
                item
                for item in items
                if analytics_by_agent.get(item.agent_id) is not None
                and analytics_by_agent[item.agent_id].attention_level == attention_level
            ]
        return items

    def summarize_by_agent(self) -> list[AgentEvaluationAnalyticsItemResponse]:
        evaluations = self.list_evaluations()
        grouped: dict[str, list[AgentEvaluationSummaryResponse]] = {}
        for item in evaluations:
            grouped.setdefault(item.agent_id, []).append(item)

        result: list[AgentEvaluationAnalyticsItemResponse] = []
        for agent_id, items in grouped.items():
            total = len(items)
            poor_count = sum(1 for item in items if item.result_label == "poor")
            fallback_related_count = sum(
                1 for item in items if "fallback" in (item.summary or "").lower()
            )
            poor_rate = round((poor_count / total) * 100, 2) if total else 0.0
            attention_level = (
                "high" if poor_rate >= 40 or fallback_related_count >= 2 else "normal"
            )
            result.append(
                AgentEvaluationAnalyticsItemResponse(
                    agent_id=agent_id,
                    evaluation_count=total,
                    excellent_count=sum(1 for item in items if item.result_label == "excellent"),
                    good_count=sum(1 for item in items if item.result_label == "good"),
                    poor_count=poor_count,
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
                    poor_rate=poor_rate,
                    fallback_related_count=fallback_related_count,
                    attention_level=attention_level,
                )
            )
        return sorted(result, key=lambda item: item.average_overall_score, reverse=True)

    def build_analytics_overview(self) -> AgentEvaluationAnalyticsOverviewResponse:
        evaluations = self.list_evaluations()
        analytics = self.summarize_by_agent()
        total = len(evaluations)
        if total == 0:
            return AgentEvaluationAnalyticsOverviewResponse()
        return AgentEvaluationAnalyticsOverviewResponse(
            evaluation_count=total,
            agent_count=len({item.agent_id for item in evaluations}),
            poor_evaluation_count=sum(1 for item in evaluations if item.result_label == "poor"),
            high_attention_agent_count=sum(
                1 for item in analytics if item.attention_level == "high"
            ),
            average_overall_score=round(
                sum(item.overall_score for item in evaluations) / total,
                2,
            ),
            average_efficiency_score=round(
                sum(item.efficiency_score for item in evaluations) / total,
                2,
            ),
            average_tool_usage_score=round(
                sum(item.tool_usage_score for item in evaluations) / total,
                2,
            ),
        )

    def list_focus_agents(self, limit: int = 10) -> list[AgentEvaluationFocusAgentResponse]:
        analytics = self.summarize_by_agent()
        suggestions = self.list_optimization_suggestions()
        suggestion_map: dict[str, list[AgentOptimizationSuggestionResponse]] = {}
        for item in suggestions:
            if not item.target_ref:
                continue
            suggestion_map.setdefault(item.target_ref, []).append(item)

        result: list[AgentEvaluationFocusAgentResponse] = []
        for item in analytics:
            agent_suggestions = suggestion_map.get(item.agent_id, [])
            suggestion_count = len(agent_suggestions)
            backlog_suggestion_count = sum(
                1 for suggestion in agent_suggestions if suggestion.status != "completed"
            )
            high_priority_backlog_count = sum(
                1
                for suggestion in agent_suggestions
                if suggestion.priority == "high" and suggestion.status != "completed"
            )
            ticket_bound_suggestion_count = sum(
                1 for suggestion in agent_suggestions if suggestion.ticket_id
            )
            completed_ticket_count = sum(
                1
                for suggestion in agent_suggestions
                if suggestion.ticket_id and suggestion.ticket_status in {"resolved", "closed"}
            )
            governance_score = round(
                max(
                    0.0,
                    100
                    - item.poor_rate * 0.35
                    - backlog_suggestion_count * 6
                    - high_priority_backlog_count * 8
                    + completed_ticket_count * 3,
                ),
                2,
            )
            focus_reason = self._build_focus_reason(
                attention_level=item.attention_level,
                poor_rate=item.poor_rate,
                backlog_suggestion_count=backlog_suggestion_count,
                high_priority_backlog_count=high_priority_backlog_count,
                fallback_related_count=item.fallback_related_count,
            )
            result.append(
                AgentEvaluationFocusAgentResponse(
                    agent_id=item.agent_id,
                    attention_level=item.attention_level,
                    average_overall_score=item.average_overall_score,
                    evaluation_count=item.evaluation_count,
                    poor_rate=item.poor_rate,
                    suggestion_count=suggestion_count,
                    backlog_suggestion_count=backlog_suggestion_count,
                    high_priority_backlog_count=high_priority_backlog_count,
                    ticket_bound_suggestion_count=ticket_bound_suggestion_count,
                    completed_ticket_count=completed_ticket_count,
                    governance_score=governance_score,
                    focus_reason=focus_reason,
                )
            )

        ranked = sorted(
            result,
            key=lambda focus: (
                0 if focus.attention_level == "high" else 1,
                -focus.high_priority_backlog_count,
                -focus.backlog_suggestion_count,
                focus.governance_score,
                focus.average_overall_score,
            ),
        )
        return ranked[: max(limit, 1)]

    def summarize_dimensions(self) -> list[AgentEvaluationDimensionAnalyticsResponse]:
        with self._session_factory() as session:
            details = self._repository.list_all_details(session)

        suggestions = self.list_optimization_suggestions()
        suggestion_map: dict[str, int] = {}
        for item in suggestions:
            if item.source_ref:
                suggestion_map[item.source_ref] = suggestion_map.get(item.source_ref, 0) + 1

        grouped: dict[str, list] = {}
        for item in details:
            grouped.setdefault(item.dimension_code, []).append(item)

        result: list[AgentEvaluationDimensionAnalyticsResponse] = []
        for dimension_code, items in grouped.items():
            total = len(items)
            low_score_count = sum(1 for item in items if item.score < 80)
            low_score_rate = round((low_score_count / total) * 100, 2) if total else 0.0
            problem_type_counts: dict[str, int] = {}
            for item in items:
                if item.problem_type:
                    problem_type_counts[item.problem_type] = (
                        problem_type_counts.get(item.problem_type, 0) + 1
                    )
            top_problem_types = [
                name
                for name, _count in sorted(
                    problem_type_counts.items(),
                    key=lambda pair: (-pair[1], pair[0]),
                )[:3]
            ]
            attention_level = "high" if low_score_rate >= 40 or low_score_count >= 2 else "normal"
            result.append(
                AgentEvaluationDimensionAnalyticsResponse(
                    dimension_code=dimension_code,
                    dimension_name=items[0].dimension_name,
                    evaluation_count=total,
                    average_score=round(sum(item.score for item in items) / total, 2),
                    low_score_count=low_score_count,
                    low_score_rate=low_score_rate,
                    related_suggestion_count=suggestion_map.get(dimension_code, 0),
                    attention_level=attention_level,
                    top_problem_types=top_problem_types,
                    improvement_hint=self._build_dimension_improvement_hint(
                        dimension_code=dimension_code,
                        low_score_rate=low_score_rate,
                        related_suggestion_count=suggestion_map.get(dimension_code, 0),
                    ),
                )
            )

        return sorted(
            result,
            key=lambda item: (
                0 if item.attention_level == "high" else 1,
                item.average_score,
                -item.related_suggestion_count,
                item.dimension_code,
            ),
        )

    def summarize_root_causes(self) -> list[AgentEvaluationRootCauseAnalyticsResponse]:
        with self._session_factory() as session:
            details = self._repository.list_all_details(session)

        suggestions = self.list_optimization_suggestions()
        suggestion_groups: dict[str, list[AgentOptimizationSuggestionResponse]] = {}
        for item in suggestions:
            if not item.source_ref:
                continue
            suggestion_groups.setdefault(item.source_ref, []).append(item)

        grouped: dict[str, list] = {}
        for item in details:
            grouped.setdefault(item.dimension_code, []).append(item)

        root_cause_names = {
            "completion": "任务收口不足",
            "tool_usage": "工具编排不稳",
            "efficiency": "执行效率波动",
            "compliance": "合规控制薄弱",
        }

        results: list[AgentEvaluationRootCauseAnalyticsResponse] = []
        for root_cause_code, items in grouped.items():
            total = len(items)
            if total == 0:
                continue
            average_score = round(sum(item.score for item in items) / total, 2)
            low_score_count = sum(1 for item in items if item.score < 80)
            related_suggestions = suggestion_groups.get(root_cause_code, [])
            high_priority_suggestion_count = sum(
                1 for item in related_suggestions if item.priority == "high"
            )
            backlog_suggestion_count = sum(
                1 for item in related_suggestions if item.status != "completed"
            )
            attention_level = (
                "high"
                if average_score < 80
                or low_score_count >= 2
                or high_priority_suggestion_count > 0
                else "normal"
            )
            results.append(
                AgentEvaluationRootCauseAnalyticsResponse(
                    root_cause_code=root_cause_code,
                    root_cause_name=root_cause_names.get(root_cause_code, root_cause_code),
                    evaluation_count=total,
                    low_score_count=low_score_count,
                    average_score=average_score,
                    related_suggestion_count=len(related_suggestions),
                    high_priority_suggestion_count=high_priority_suggestion_count,
                    backlog_suggestion_count=backlog_suggestion_count,
                    attention_level=attention_level,
                    impact_summary=self._build_root_cause_impact_summary(
                        root_cause_code=root_cause_code,
                        average_score=average_score,
                        low_score_count=low_score_count,
                        evaluation_count=total,
                    ),
                    recommended_action=self._build_root_cause_recommended_action(
                        root_cause_code=root_cause_code,
                        backlog_suggestion_count=backlog_suggestion_count,
                        high_priority_suggestion_count=high_priority_suggestion_count,
                    ),
                )
            )

        return sorted(
            results,
            key=lambda item: (
                0 if item.attention_level == "high" else 1,
                -item.high_priority_suggestion_count,
                -item.backlog_suggestion_count,
                item.average_score,
                item.root_cause_code,
            ),
        )

    def build_evaluation_trend(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> AgentEvaluationTrendResponse:
        evaluations = self.list_evaluations()
        if agent_id:
            evaluations = [item for item in evaluations if item.agent_id == agent_id]
        trend_items = sorted(
            evaluations,
            key=lambda item: datetime.fromisoformat(item.create_time),
        )[-max(limit, 1) :]
        if not trend_items:
            return AgentEvaluationTrendResponse(agent_id=agent_id)

        poor_count = sum(1 for item in trend_items if item.result_label == "poor")
        latest = trend_items[-1]
        previous = trend_items[-2] if len(trend_items) > 1 else None
        previous_score = previous.overall_score if previous is not None else None
        score_delta = round(latest.overall_score - (previous_score or latest.overall_score), 2)
        attention_level = "high" if poor_count >= 2 or latest.overall_score < 75 else "normal"
        return AgentEvaluationTrendResponse(
            agent_id=agent_id or latest.agent_id,
            evaluation_count=len(trend_items),
            average_overall_score=round(
                sum(item.overall_score for item in trend_items) / len(trend_items),
                2,
            ),
            latest_overall_score=latest.overall_score,
            previous_overall_score=previous_score,
            score_delta=score_delta,
            improving=score_delta >= 0,
            poor_count=poor_count,
            attention_level=attention_level,
            points=[
                AgentEvaluationTrendPointResponse(
                    evaluation_id=item.evaluation_id,
                    task_id=item.task_id,
                    agent_id=item.agent_id,
                    overall_score=item.overall_score,
                    result_label=item.result_label,
                    create_time=item.create_time,
                )
                for item in trend_items
            ],
        )

    @staticmethod
    def _build_dimension_improvement_hint(
        *,
        dimension_code: str,
        low_score_rate: float,
        related_suggestion_count: int,
    ) -> str:
        if dimension_code == "tool_usage":
            return "优先收敛工具选择规则，减少低收益调用，并补执行前判断。"
        if dimension_code == "efficiency":
            return "优先优化执行链路时延、fallback 频率与中间步骤数量。"
        if dimension_code == "compliance":
            return "优先补审批绑定、审计留痕和敏感访问控制策略。"
        if dimension_code == "completion":
            return "优先强化任务目标、输出格式与结果收口约束。"
        if related_suggestion_count > 0 or low_score_rate >= 30:
            return "建议结合已有优化建议，优先治理该维度的高频失分问题。"
        return "当前维度整体稳定，可继续观察趋势变化。"

    @staticmethod
    def _build_focus_reason(
        *,
        attention_level: str,
        poor_rate: float,
        backlog_suggestion_count: int,
        high_priority_backlog_count: int,
        fallback_related_count: int,
    ) -> str:
        reasons: list[str] = []
        if attention_level == "high":
            reasons.append("高关注")
        if poor_rate >= 40:
            reasons.append(f"低分率 {poor_rate}%")
        if high_priority_backlog_count > 0:
            reasons.append(f"高优积压 {high_priority_backlog_count}")
        elif backlog_suggestion_count > 0:
            reasons.append(f"建议积压 {backlog_suggestion_count}")
        if fallback_related_count > 0:
            reasons.append(f"fallback 关联 {fallback_related_count}")
        return " / ".join(reasons) if reasons else "运行平稳"

    @staticmethod
    def _build_root_cause_impact_summary(
        *,
        root_cause_code: str,
        average_score: float,
        low_score_count: int,
        evaluation_count: int,
    ) -> str:
        if root_cause_code == "tool_usage":
            return (
                f"该类问题覆盖 {evaluation_count} 条评估，平均分 {average_score}，"
                f"其中 {low_score_count} 条出现工具使用低分，直接影响执行稳定性。"
            )
        if root_cause_code == "efficiency":
            return (
                f"该类问题覆盖 {evaluation_count} 条评估，平均分 {average_score}，"
                f"其中 {low_score_count} 条存在效率低分，主要影响端到端响应时延。"
            )
        if root_cause_code == "compliance":
            return (
                f"该类问题覆盖 {evaluation_count} 条评估，平均分 {average_score}，"
                f"其中 {low_score_count} 条存在合规低分，影响高风险流程可追溯性。"
            )
        if root_cause_code == "completion":
            return (
                f"该类问题覆盖 {evaluation_count} 条评估，平均分 {average_score}，"
                f"其中 {low_score_count} 条出现任务收口不足，影响结果交付质量。"
            )
        return (
            f"该类问题覆盖 {evaluation_count} 条评估，平均分 {average_score}，"
            f"其中 {low_score_count} 条为低分样本。"
        )

    @staticmethod
    def _build_root_cause_recommended_action(
        *,
        root_cause_code: str,
        backlog_suggestion_count: int,
        high_priority_suggestion_count: int,
    ) -> str:
        base_map = {
            "completion": "优先补强结果模板、输出约束和任务收口策略。",
            "tool_usage": "优先收敛工具清单、补充工具选择规则和降级策略。",
            "efficiency": "优先压缩执行链路、减少中间阶段和 fallback 触发。",
            "compliance": "优先补审批绑定、审计留痕和敏感访问控制。",
        }
        base = base_map.get(root_cause_code, "优先排查该维度高频低分样本并补齐治理动作。")
        if high_priority_suggestion_count > 0:
            return f"{base} 当前已有 {high_priority_suggestion_count} 条高优先建议待推进。"
        if backlog_suggestion_count > 0:
            return f"{base} 当前仍有 {backlog_suggestion_count} 条未闭环建议。"
        return f"{base} 当前建议存量较轻，可继续观察趋势。"

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

    def list_optimization_suggestions(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
    ) -> list[AgentOptimizationSuggestionResponse]:
        with self._session_factory() as session:
            items = self._repository.list_all_suggestions(
                session,
                agent_id=agent_id,
                status=status,
                owner=owner,
                priority=priority,
            )
            return [self._to_suggestion(item) for item in items]

    def build_optimization_suggestion_overview(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
    ) -> AgentOptimizationSuggestionOverviewResponse:
        items = self.list_optimization_suggestions(
            agent_id=agent_id,
            status=status,
            owner=owner,
            priority=priority,
        )
        total = len(items)
        ticket_bound_count = sum(1 for item in items if item.ticket_id)
        completed_ticket_count = sum(
            1
            for item in items
            if item.ticket_id and item.ticket_status in {"resolved", "closed"}
        )
        backlog_count = sum(1 for item in items if item.status != "completed")
        high_priority_backlog_count = sum(
            1
            for item in items
            if item.priority == "high" and item.status != "completed"
        )
        completion_rate = round(
            (sum(1 for item in items if item.status == "completed") / total) * 100,
            2,
        ) if total else 0.0
        return AgentOptimizationSuggestionOverviewResponse(
            total=total,
            new_count=sum(1 for item in items if item.status == "new"),
            in_progress_count=sum(1 for item in items if item.status == "in_progress"),
            completed_count=sum(1 for item in items if item.status == "completed"),
            high_priority_count=sum(1 for item in items if item.priority == "high"),
            ticket_bound_count=ticket_bound_count,
            ticket_unbound_count=total - ticket_bound_count,
            completed_ticket_count=completed_ticket_count,
            backlog_count=backlog_count,
            high_priority_backlog_count=high_priority_backlog_count,
            completion_rate=completion_rate,
        )

    def build_execution_backlog(
        self,
        *,
        agent_id: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
        backlog_only: bool = False,
    ) -> AgentOptimizationExecutionBacklogResponse:
        items = self.list_optimization_suggestions(
            agent_id=agent_id,
            owner=owner,
            priority=priority,
        )
        backlog_items: list[AgentOptimizationExecutionBacklogItemResponse] = []
        now = datetime.utcnow()
        overdue_threshold = now - timedelta(days=3)

        with self._session_factory() as session:
            for suggestion in items:
                evaluation = self._repository.get_evaluation(session, suggestion.evaluation_id)
                update_time = self._parse_iso_datetime(suggestion.update_time)
                create_time = self._parse_iso_datetime(suggestion.create_time)
                reference_time = update_time or create_time or now
                overdue = (
                    suggestion.status != "completed"
                    and reference_time <= overdue_threshold
                )
                aging_days = max(0, int((now - reference_time).total_seconds() // 86400))
                execution_stage = self._resolve_execution_stage(suggestion)
                attention_level = self._resolve_execution_attention(
                    suggestion=suggestion,
                    execution_stage=execution_stage,
                    overdue=overdue,
                )
                recommended_action = self._build_execution_recommended_action(
                    suggestion=suggestion,
                    execution_stage=execution_stage,
                    overdue=overdue,
                )
                backlog_items.append(
                    AgentOptimizationExecutionBacklogItemResponse(
                        suggestion_id=suggestion.suggestion_id,
                        evaluation_id=suggestion.evaluation_id,
                        task_id=evaluation.task_id if evaluation is not None else None,
                        agent_id=suggestion.agent_id,
                        optimization_type=suggestion.optimization_type,
                        priority=suggestion.priority,
                        status=suggestion.status,
                        owner=suggestion.owner,
                        ticket_id=suggestion.ticket_id,
                        ticket_status=suggestion.ticket_status,
                        execution_stage=execution_stage,
                        attention_level=attention_level,
                        overdue=overdue,
                        aging_days=aging_days,
                        current_value_summary=suggestion.current_value_summary,
                        suggested_change=suggestion.suggested_change,
                        recommended_action=recommended_action,
                        create_time=suggestion.create_time,
                        update_time=suggestion.update_time,
                        closed_at=suggestion.closed_at,
                    )
                )

        if backlog_only:
            backlog_items = [item for item in backlog_items if item.status != "completed"]

        backlog_items = sorted(
            backlog_items,
            key=lambda item: (
                0 if item.attention_level == "high" else 1,
                0 if item.priority == "high" else 1 if item.priority == "medium" else 2,
                0 if item.overdue else 1,
                -item.aging_days,
                item.suggestion_id,
            ),
        )

        total = len(backlog_items)
        return AgentOptimizationExecutionBacklogResponse(
            total=total,
            untriaged_count=sum(1 for item in backlog_items if item.execution_stage == "untriaged"),
            ticket_pending_count=sum(
                1 for item in backlog_items if item.execution_stage == "ticket_pending"
            ),
            processing_count=sum(1 for item in backlog_items if item.execution_stage == "processing"),
            completed_count=sum(1 for item in backlog_items if item.execution_stage == "completed"),
            overdue_count=sum(1 for item in backlog_items if item.overdue),
            high_priority_backlog_count=sum(
                1
                for item in backlog_items
                if item.priority == "high" and item.status != "completed"
            ),
            automation_ready_count=sum(
                1
                for item in backlog_items
                if item.execution_stage in {"untriaged", "ticket_pending"}
                and item.priority in {"high", "medium"}
            ),
            closed_loop_count=sum(1 for item in backlog_items if item.ticket_id and item.status == "completed"),
            items=backlog_items,
        )

    def build_execution_plan(
        self,
        *,
        agent_id: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
    ) -> AgentOptimizationExecutionPlanResponse:
        backlog = self.build_execution_backlog(
            agent_id=agent_id,
            owner=owner,
            priority=priority,
            backlog_only=False,
        )
        grouped: dict[str, list[AgentOptimizationExecutionBacklogItemResponse]] = {}
        for item in backlog.items:
            grouped.setdefault(item.agent_id, []).append(item)

        results: list[AgentOptimizationExecutionPlanItemResponse] = []
        for current_agent_id, items in grouped.items():
            backlog_count = sum(1 for item in items if item.status != "completed")
            high_priority_count = sum(1 for item in items if item.priority == "high")
            automation_ready_count = sum(
                1
                for item in items
                if item.execution_stage in {"untriaged", "ticket_pending"}
                and item.priority in {"high", "medium"}
            )
            overdue_count = sum(1 for item in items if item.overdue)
            blocked_count = sum(
                1 for item in items if item.execution_stage == "ticket_pending" and not item.ticket_id
            )
            owner_count = len({item.owner for item in items if item.owner})
            target_refs = sorted({item.optimization_type for item in items})
            owners = sorted({item.owner for item in items if item.owner})
            dependency_ticket_ids = sorted({item.ticket_id for item in items if item.ticket_id})
            recommended_actions = self._build_execution_plan_actions(items)
            attention_level = (
                "high"
                if overdue_count > 0 or high_priority_count > 0 or blocked_count > 0
                else "normal"
            )
            next_step = recommended_actions[0] if recommended_actions else "持续跟踪优化执行进度。"
            results.append(
                AgentOptimizationExecutionPlanItemResponse(
                    agent_id=current_agent_id,
                    suggestion_count=len(items),
                    backlog_count=backlog_count,
                    high_priority_count=high_priority_count,
                    automation_ready_count=automation_ready_count,
                    overdue_count=overdue_count,
                    blocked_count=blocked_count,
                    owner_count=owner_count,
                    target_refs=target_refs,
                    owners=owners,
                    dependency_ticket_ids=dependency_ticket_ids,
                    recommended_actions=recommended_actions,
                    next_step=next_step,
                    attention_level=attention_level,
                )
            )

        results = sorted(
            results,
            key=lambda item: (
                0 if item.attention_level == "high" else 1,
                -item.overdue_count,
                -item.high_priority_count,
                -item.automation_ready_count,
                item.agent_id,
            ),
        )
        return AgentOptimizationExecutionPlanResponse(
            total_agents=len(results),
            high_attention_agent_count=sum(1 for item in results if item.attention_level == "high"),
            automation_ready_agent_count=sum(1 for item in results if item.automation_ready_count > 0),
            blocked_agent_count=sum(1 for item in results if item.blocked_count > 0),
            items=results,
        )

    def update_optimization_suggestion(
        self,
        suggestion_id: int,
        request: AgentOptimizationSuggestionUpdateRequest,
    ) -> AgentOptimizationSuggestionResponse | None:
        with self._session_factory() as session:
            item = self._repository.update_suggestion(
                session,
                suggestion_id=suggestion_id,
                status=request.status,
                owner=request.owner,
                priority=request.priority,
            )
            if item is None:
                return None
            session.commit()
            session.refresh(item)
            return self._to_suggestion(item)

    def get_suggestion_audit_context(self, suggestion_id: int) -> dict[str, str | int | None] | None:
        with self._session_factory() as session:
            suggestion = self._repository.get_suggestion(session, suggestion_id)
            if suggestion is None:
                return None
            evaluation = self._repository.get_evaluation(session, suggestion.evaluation_id)
            return {
                "suggestion_id": suggestion.id,
                "evaluation_id": suggestion.evaluation_id,
                "task_id": evaluation.task_id if evaluation is not None else None,
                "agent_id": suggestion.agent_id,
                "optimization_type": suggestion.optimization_type,
                "target_ref": suggestion.target_ref,
            }

    def create_suggestion_ticket(
        self,
        suggestion_id: int,
        request: AgentOptimizationSuggestionTicketRequest,
    ) -> AgentOptimizationSuggestionResponse | None:
        with self._session_factory() as session:
            suggestion = self._repository.get_suggestion(session, suggestion_id)
            if suggestion is None:
                return None
            if suggestion.ticket_id:
                return self._to_suggestion(suggestion)
            evaluation = self._repository.get_evaluation(session, suggestion.evaluation_id)

            ticket_id = f"EVAL-{uuid4().hex[:8].upper()}"
            description_lines = [
                f"evaluation_id={suggestion.evaluation_id}",
                f"suggestion_id={suggestion.id}",
                f"agent_id={suggestion.agent_id}",
                f"optimization_type={suggestion.optimization_type}",
                f"target_ref={suggestion.target_ref or '-'}",
                f"source_type={suggestion.source_type or '-'}",
                f"source_ref={suggestion.source_ref or '-'}",
                "",
                "current_value_summary:",
                suggestion.current_value_summary or "-",
                "",
                "suggested_change:",
                suggestion.suggested_change,
            ]
            if request.comment:
                description_lines.extend(["", "comment:", request.comment])

            session.add(
                ServiceTicketModel(
                    ticket_id=ticket_id,
                    biz_domain="operations",
                    category="agent_optimization",
                    priority=request.priority or suggestion.priority,
                    title=f"评估优化任务/{suggestion.optimization_type}",
                    description="\n".join(description_lines),
                    status="submitted",
                    requested_by=request.requested_by,
                    owner=request.owner or request.requested_by,
                    source="evaluation",
                    payload={
                        "suggestion_id": suggestion.id,
                        "evaluation_id": suggestion.evaluation_id,
                        "task_id": evaluation.task_id if evaluation is not None else None,
                        "agent_id": suggestion.agent_id,
                        "optimization_type": suggestion.optimization_type,
                        "target_ref": suggestion.target_ref,
                        "source_type": suggestion.source_type,
                        "source_ref": suggestion.source_ref,
                    },
                )
            )
            item = self._repository.bind_ticket(
                session,
                suggestion_id=suggestion_id,
                ticket_id=ticket_id,
                ticket_status="submitted",
                owner=request.owner,
                priority=request.priority,
            )
            session.commit()
            if item is None:
                return None
            session.refresh(item)
            return self._to_suggestion(item)

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
            f"本次观测到 {len(runtime_facts.observations)} 条运行观测，"
            f"{len(runtime_facts.tool_calls)} 次工具调用，"
            f"fallback {runtime_facts.fallback_count} 次，"
            "可用于后续路由优化、提示词优化和工具编排调整。"
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
                "suggestion": "继续补强结果结构化输出，让任务结论更容易复核和回收。",
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
                "suggested_change": "补充任务目标、输出格式和边界条件描述，提升回答稳定性与一致性。",
                "priority": "medium",
                "source_type": "evaluation_dimension",
                "source_ref": "completion",
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
                    "source_type": "evaluation_dimension",
                    "source_ref": "tool_usage",
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
                    "suggested_change": (
                        "补齐 AgentScope 模型桥接配置或增强 runtime session 编排，降低本地 fallback 比例。"
                    ),
                    "priority": "high",
                    "source_type": "runtime_fact",
                    "source_ref": "fallback_count",
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
                    "source_type": "evaluation_dimension",
                    "source_ref": "efficiency",
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
            suggestion_id=item.id,
            evaluation_id=item.evaluation_id,
            agent_id=item.agent_id,
            optimization_type=item.optimization_type,
            target_ref=item.target_ref,
            current_value_summary=item.current_value_summary or "",
            suggested_change=item.suggested_change,
            priority=item.priority,
            status=item.status,
            owner=item.owner,
            source_type=item.source_type,
            source_ref=item.source_ref,
            ticket_id=item.ticket_id,
            ticket_status=item.ticket_status,
            closed_at=item.closed_at.isoformat() if item.closed_at else None,
            create_time=item.create_time.isoformat() if item.create_time else "",
            update_time=item.update_time.isoformat() if item.update_time else "",
        )

    @staticmethod
    def _parse_iso_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _resolve_execution_stage(suggestion: AgentOptimizationSuggestionResponse) -> str:
        if suggestion.status == "completed":
            return "completed"
        if not suggestion.ticket_id:
            return "untriaged" if suggestion.status == "new" else "ticket_pending"
        if suggestion.ticket_status in {"resolved", "closed"}:
            return "completed"
        return "processing"

    @staticmethod
    def _resolve_execution_attention(
        *,
        suggestion: AgentOptimizationSuggestionResponse,
        execution_stage: str,
        overdue: bool,
    ) -> str:
        if overdue:
            return "high"
        if suggestion.priority == "high" and execution_stage != "completed":
            return "high"
        return "normal"

    @staticmethod
    def _build_execution_recommended_action(
        *,
        suggestion: AgentOptimizationSuggestionResponse,
        execution_stage: str,
        overdue: bool,
    ) -> str:
        if execution_stage == "untriaged":
            return "优先分配 owner 并评估是否需要立即转工单。"
        if execution_stage == "ticket_pending":
            return "建议补全执行负责人并转为治理工单，进入实际优化实施。"
        if overdue:
            return "当前建议已超时未闭环，建议升级优先级并触发治理复盘。"
        if execution_stage == "processing":
            return "持续跟踪工单处理进度，确认变更已在运行链路生效。"
        return "建议回收优化结果并沉淀为标准配置或执行模板。"

    @staticmethod
    def _build_execution_plan_actions(
        items: list[AgentOptimizationExecutionBacklogItemResponse],
    ) -> list[str]:
        actions: list[str] = []
        if any(item.overdue for item in items):
            actions.append("优先处理超时积压项，并安排治理复盘。")
        if any(
            item.execution_stage in {"untriaged", "ticket_pending"} and item.priority == "high"
            for item in items
        ):
            actions.append("先推进高优建议分诊和工单化，避免长期停留在分析阶段。")
        if any(item.execution_stage == "processing" for item in items):
            actions.append("跟进处理中工单，确认优化已落到实际 Agent 配置与运行链路。")
        if any(not item.owner for item in items if item.status != "completed"):
            actions.append("补齐责任人归属，减少执行链路空转。")
        if not actions:
            actions.append("当前闭环节奏稳定，建议持续回收优化成果并标准化。")
        return actions[:3]
