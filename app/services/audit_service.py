from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.audit_repository import AuditRepository
from app.schemas import (
    AuditContextDrilldownResponse,
    AuditContextTargetResponse,
    AuditEventResponse,
    AuditExecutionPlanRunResponse,
    AuditExecutionPlanRunsResponse,
    AuditLinkedContextItemResponse,
    AuditLinkedContextResponse,
    AuditOverviewResponse,
)


class AuditService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: AuditRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def record(self, action: str, actor_id: str, payload: Dict[str, Any]) -> None:
        normalized_payload = self._normalize_payload(action=action, actor_id=actor_id, payload=payload)
        with session_scope(self._session_factory) as session:
            self._repository.create(
                session,
                action=action,
                actor_id=actor_id,
                payload=normalized_payload,
            )

    def list_events(
        self,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        source: str | None = None,
        event_type: str | None = None,
        outcome: int | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        capability_id: str | None = None,
        workflow: str | None = None,
        ticket_id: str | None = None,
        suggestion_id: int | None = None,
        evaluation_id: str | None = None,
    ) -> List[AuditEventResponse]:
        with self._session_factory() as session:
            return self._repository.list_events(
                session,
                action=action,
                actor_id=actor_id,
                source=source,
                event_type=event_type,
                outcome=outcome,
                task_id=task_id,
                approval_id=approval_id,
                capability_id=capability_id,
                workflow=workflow,
                ticket_id=ticket_id,
                suggestion_id=suggestion_id,
                evaluation_id=evaluation_id,
            )

    def build_overview(self) -> AuditOverviewResponse:
        items = self.list_events()
        source_counts: dict[str, int] = {}
        event_type_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        linked_context_counts = {
            "task": 0,
            "approval": 0,
            "capability": 0,
            "workflow": 0,
            "ticket": 0,
            "suggestion": 0,
            "evaluation": 0,
        }
        success_count = 0
        failed_count = 0
        pending_count = 0

        for item in items:
            source_key = item.source or "unknown"
            event_type_key = item.event_type or "unknown"
            action_key = item.action or "unknown"
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            event_type_counts[event_type_key] = event_type_counts.get(event_type_key, 0) + 1
            action_counts[action_key] = action_counts.get(action_key, 0) + 1

            if item.task_id:
                linked_context_counts["task"] += 1
            if item.approval_id:
                linked_context_counts["approval"] += 1
            if item.capability_id:
                linked_context_counts["capability"] += 1
            if item.workflow:
                linked_context_counts["workflow"] += 1
            if item.ticket_id:
                linked_context_counts["ticket"] += 1
            if item.suggestion_id is not None:
                linked_context_counts["suggestion"] += 1
            if item.evaluation_id:
                linked_context_counts["evaluation"] += 1

            if item.outcome == 1:
                success_count += 1
            elif item.outcome == 2:
                failed_count += 1
            else:
                pending_count += 1

        return AuditOverviewResponse(
            total=len(items),
            success_count=success_count,
            failed_count=failed_count,
            pending_count=pending_count,
            source_counts=source_counts,
            event_type_counts=event_type_counts,
            action_counts=action_counts,
            linked_context_counts=linked_context_counts,
        )

    def build_linked_context(
        self,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        source: str | None = None,
        event_type: str | None = None,
        outcome: int | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        capability_id: str | None = None,
        workflow: str | None = None,
        ticket_id: str | None = None,
        suggestion_id: int | None = None,
        evaluation_id: str | None = None,
    ) -> AuditLinkedContextResponse:
        items = self.list_events(
            action=action,
            actor_id=actor_id,
            source=source,
            event_type=event_type,
            outcome=outcome,
            task_id=task_id,
            approval_id=approval_id,
            capability_id=capability_id,
            workflow=workflow,
            ticket_id=ticket_id,
            suggestion_id=suggestion_id,
            evaluation_id=evaluation_id,
        )

        context_aliases = {
            "task": ("task_id",),
            "approval": ("approval_id",),
            "capability": ("capability_id",),
            "workflow": ("workflow",),
            "ticket": ("ticket_id",),
            "suggestion": ("suggestion_id",),
            "evaluation": ("evaluation_id",),
        }
        context_counts = {key: 0 for key in context_aliases}
        grouped: dict[tuple[str, str], dict[str, object]] = {}

        for item in items:
            payload = item.payload or {}
            for context_type, keys in context_aliases.items():
                context_value = None
                for key in keys:
                    direct_value = getattr(item, key, None)
                    if direct_value not in (None, ""):
                        context_value = direct_value
                        break
                    payload_value = payload.get(key)
                    if payload_value not in (None, ""):
                        context_value = payload_value
                        break
                if context_value in (None, ""):
                    continue

                context_id = str(context_value)
                context_counts[context_type] += 1
                group_key = (context_type, context_id)
                bucket = grouped.setdefault(
                    group_key,
                    {
                        "actions": set(),
                        "event_count": 0,
                        "latest_created_at": "",
                        "latest_action": None,
                        "latest_actor_id": None,
                    },
                )
                bucket["event_count"] = int(bucket["event_count"]) + 1
                cast_actions = bucket["actions"]
                if isinstance(cast_actions, set):
                    cast_actions.add(item.action)
                created_at = item.created_at or ""
                if created_at >= str(bucket["latest_created_at"] or ""):
                    bucket["latest_created_at"] = created_at
                    bucket["latest_action"] = item.action
                    bucket["latest_actor_id"] = item.actor_id

        context_items = [
            AuditLinkedContextItemResponse(
                context_type=context_type,
                context_id=context_id,
                event_count=int(bucket["event_count"]),
                actions=sorted(list(bucket["actions"])) if isinstance(bucket["actions"], set) else [],
                latest_action=(
                    str(bucket["latest_action"]) if bucket["latest_action"] is not None else None
                ),
                latest_actor_id=(
                    str(bucket["latest_actor_id"])
                    if bucket["latest_actor_id"] is not None
                    else None
                ),
                latest_created_at=(
                    str(bucket["latest_created_at"])
                    if bucket["latest_created_at"]
                    else None
                ),
            )
            for (context_type, context_id), bucket in grouped.items()
        ]
        context_items.sort(
            key=lambda item: (
                -item.event_count,
                item.context_type,
                item.context_id,
            )
        )

        return AuditLinkedContextResponse(
            total_events=len(items),
            context_counts=context_counts,
            items=context_items,
        )

    def build_context_drilldown(
        self,
        *,
        context_type: str,
        context_id: str,
    ) -> AuditContextDrilldownResponse:
        valid_context_types = {
            "task",
            "approval",
            "capability",
            "workflow",
            "ticket",
            "suggestion",
            "evaluation",
        }
        if context_type not in valid_context_types:
            raise ValueError(f"unsupported context_type: {context_type}")

        filters: dict[str, Any] = {}
        if context_type == "task":
            filters["task_id"] = context_id
        elif context_type == "approval":
            filters["approval_id"] = context_id
        elif context_type == "capability":
            filters["capability_id"] = context_id
        elif context_type == "workflow":
            filters["workflow"] = context_id
        elif context_type == "ticket":
            filters["ticket_id"] = context_id
        elif context_type == "suggestion":
            try:
                filters["suggestion_id"] = int(context_id)
            except ValueError:
                filters["suggestion_id"] = -1
        elif context_type == "evaluation":
            filters["evaluation_id"] = context_id

        events = self.list_events(**filters)
        actions = sorted({item.action for item in events})
        latest = events[0] if events else None
        return AuditContextDrilldownResponse(
            context_type=context_type,
            context_id=context_id,
            event_count=len(events),
            actions=actions,
            latest_action=latest.action if latest else None,
            latest_actor_id=latest.actor_id if latest else None,
            latest_created_at=latest.created_at if latest else None,
            target=self._build_context_target(context_type, context_id),
            events=events,
        )

    def list_execution_plan_runs(
        self,
        *,
        actor_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> AuditExecutionPlanRunsResponse:
        items = self.list_events(
            action="evaluation.execution_plan.apply",
            actor_id=actor_id,
            capability_id=agent_id,
        )
        results: list[AuditExecutionPlanRunResponse] = []
        for item in items[: max(limit, 1)]:
            nested_payload = (item.payload or {}).get("payload", {})
            results.append(
                AuditExecutionPlanRunResponse(
                    action=item.action,
                    actor_id=item.actor_id,
                    created_at=item.created_at,
                    agent_id=nested_payload.get("agent_id") or item.capability_id,
                    owner=nested_payload.get("owner"),
                    priority=nested_payload.get("priority"),
                    max_items=nested_payload.get("max_items", 0),
                    candidate_count=nested_payload.get("candidate_count", 0),
                    processed_count=nested_payload.get("processed_count", 0),
                    created_ticket_count=nested_payload.get("created_ticket_count", 0),
                    suggestion_ids=nested_payload.get("suggestion_ids", []) or [],
                    ticket_ids=nested_payload.get("ticket_ids", []) or [],
                    summary=(item.payload or {}).get("response_summary", ""),
                )
            )
        return AuditExecutionPlanRunsResponse(
            total=len(results),
            total_processed_count=sum(item.processed_count for item in results),
            total_created_ticket_count=sum(item.created_ticket_count for item in results),
            items=results,
        )

    @staticmethod
    def _build_context_target(
        context_type: str,
        context_id: str,
    ) -> AuditContextTargetResponse:
        target_ui_map = {
            "task": f"/ui/tasks?task_id={context_id}",
            "capability": f"/ui/capabilities?capability_id={context_id}",
            "workflow": f"/ui/workflows?workflow_code={context_id}",
            "ticket": f"/ui/service-tickets?ticket_id={context_id}",
            "suggestion": f"/ui/evaluations?suggestion_id={context_id}",
            "evaluation": f"/ui/evaluations?evaluation_id={context_id}",
        }
        target_api_map = {
            "task": f"/api/tasks/{context_id}",
            "capability": f"/api/capabilities/{context_id}",
            "workflow": f"/api/workflows/{context_id}",
            "ticket": f"/api/service-tickets/{context_id}",
            "evaluation": f"/api/evaluations/{context_id}",
        }
        title_map = {
            "task": "任务上下文",
            "approval": "审批上下文",
            "capability": "能力上下文",
            "workflow": "流程上下文",
            "ticket": "工单上下文",
            "suggestion": "建议上下文",
            "evaluation": "评估上下文",
        }
        return AuditContextTargetResponse(
            context_type=context_type,
            context_id=context_id,
            target_ui=target_ui_map.get(context_type),
            target_api=target_api_map.get(context_type),
            title=title_map.get(context_type, context_type),
        )

    @staticmethod
    def _normalize_payload(
        *,
        action: str,
        actor_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(payload)
        nested_payload = normalized.get("payload")
        if not isinstance(nested_payload, dict):
            nested_payload = {}

        normalized.setdefault("source", "platform")
        normalized.setdefault("event_type", "audit")
        normalized.setdefault("outcome", 0)
        normalized.setdefault("action", action)
        normalized.setdefault("actor_id", actor_id)

        for field in (
            "task_id",
            "approval_id",
            "capability_id",
            "agent_id",
            "workflow",
            "workflow_id",
            "ticket_id",
            "ticket_status",
            "suggestion_id",
            "evaluation_id",
            "trace_id",
            "session_id",
            "request_summary",
            "response_summary",
            "risk_level",
            "error_code",
            "error_msg",
            "tags",
        ):
            if normalized.get(field) in (None, "") and nested_payload.get(field) not in (None, ""):
                normalized[field] = nested_payload.get(field)

        if normalized.get("workflow") in (None, "") and normalized.get("workflow_id") not in (None, ""):
            normalized["workflow"] = normalized["workflow_id"]
        return normalized
