from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.audit_repository import AuditRepository
from app.schemas import (
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
        with session_scope(self._session_factory) as session:
            self._repository.create(
                session,
                action=action,
                actor_id=actor_id,
                payload=payload,
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
