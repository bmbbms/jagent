from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from app.registry.base import CapabilityMetadata
from app.registry.remote_proxy import RemoteCapabilityProxy
from app.schemas import BizDomain, ChatRequest, RoutingTrace
from app.services.agent_gateway_routing_service import AgentGatewayRoutingService
from app.services.agent_profile_service import AgentProfileSyncService
from app.services.audit_service import AuditService
from app.services.evaluation_service import EvaluationService
from app.services.task_service import TaskService


@dataclass(frozen=True)
class AgentGatewayInvokeResult:
    task_id: str
    contact_id: str | None
    selected_agent_id: str
    selected_agent_name: str
    matched_skill_ids: list[str]
    route_reason: str
    policy_decision: str
    declared_skills: list
    declared_mcps: list
    declared_workflows: list
    summary: str
    next_action: str
    references: list[str]
    audit_tags: list[str]
    routing_trace: RoutingTrace | None
    risk_flags: list[str]


class AgentGatewayExecutionService:
    def __init__(
        self,
        *,
        routing_service: AgentGatewayRoutingService,
        agent_profile_service: AgentProfileSyncService,
        task_service: TaskService,
        audit_service: AuditService,
        evaluation_service: EvaluationService,
    ) -> None:
        self._routing_service = routing_service
        self._agent_profile_service = agent_profile_service
        self._task_service = task_service
        self._audit_service = audit_service
        self._evaluation_service = evaluation_service

    def invoke(
        self,
        *,
        user_id: str,
        biz_domain: str,
        message: str,
        requested_agent_id: str | None = None,
        tenant_id: str | None = None,
        roles: list[str] | None = None,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> AgentGatewayInvokeResult:
        biz_domain_enum = self._parse_biz_domain(biz_domain)
        request_metadata = dict(metadata or {})
        roles = roles or []
        route_payload = self._routing_service.explain_route(
            user_id=user_id,
            biz_domain=biz_domain_enum.value,
            message=message,
            requested_agent_id=requested_agent_id,
            tenant_id=tenant_id,
            roles=roles,
            source=source,
        )
        selected_agent_id = route_payload.get("selected_agent_id")
        if not selected_agent_id:
            raise ValueError("no available agent profile matched the request")

        bundle = self._agent_profile_service.get_profile_bundle(selected_agent_id)
        if bundle is None:
            raise ValueError(f"agent profile not found: {selected_agent_id}")

        profile = bundle["profile"]
        if not profile.endpoint:
            raise ValueError(f"agent profile endpoint is missing: {selected_agent_id}")

        chat_request = ChatRequest(
            user_id=user_id,
            biz_domain=biz_domain_enum,
            message=message,
            metadata={
                **request_metadata,
                "requested_agent_id": requested_agent_id,
                "gateway_selected_agent_id": selected_agent_id,
            },
        )
        runtime_task = self._task_service.create_runtime_task(
            request=chat_request,
            selected_agent_id=selected_agent_id,
            capability_name=profile.agent_name,
        )
        task_id = runtime_task["task_id"]
        contact_id = runtime_task["contact_id"]
        chat_request.metadata["_runtime_context"] = {
            **runtime_task,
            "emit_event": self._task_service.emit_runtime_event,
            "source_agent_id": "agent.gateway",
            "source_agent_name": "Main Agent Gateway",
        }

        self._emit_gateway_events(
            task_id=task_id,
            selected_agent_id=selected_agent_id,
            selected_agent_name=profile.agent_name,
            requested_agent_id=requested_agent_id,
            route_payload=route_payload,
            bundle=bundle,
        )

        proxy = RemoteCapabilityProxy(self._build_metadata(profile=profile, bundle=bundle))
        started_at = datetime.utcnow()
        try:
            response = proxy.run(chat_request)
        except Exception as exc:
            self._task_service.emit_runtime_event(
                task_id=task_id,
                event_type="gateway_invoke_failed",
                title="Gateway invoke failed",
                content=str(exc),
                event_status="failed",
                agent_id=selected_agent_id,
                event_payload={
                    "selected_agent_id": selected_agent_id,
                    "selected_agent_name": profile.agent_name,
                    "route_reason": route_payload.get("route_reason") or "",
                    "policy_decision": route_payload.get("policy_decision") or "deny",
                },
                current_stage="failed",
                task_status="failed",
            )
            self._task_service.fail_task(task_id=task_id, final_output_summary=str(exc))
            self._record_audit(
                user_id=user_id,
                task_id=task_id,
                contact_id=contact_id,
                trace_id=runtime_task["trace_id"],
                selected_agent_id=selected_agent_id,
                route_payload=route_payload,
                message=message,
                summary=str(exc),
                outcome=2,
                started_at=started_at,
                error_msg=str(exc),
            )
            raise

        response.task_id = task_id
        response.routing_trace = RoutingTrace(
            requested_domain=biz_domain_enum,
            selected_capability_id=selected_agent_id,
            candidate_capability_ids=list(route_payload.get("candidate_agent_ids") or []),
            matched_capability_ids=list(route_payload.get("allowed_agent_ids") or []),
            declared_skills=[item.skill_id for item in bundle["skills"]],
            strategy="agent_profile_policy_route",
            reason=route_payload.get("route_reason") or "",
        )
        if "agent_gateway" not in response.audit_tags:
            response.audit_tags.append("agent_gateway")

        self._task_service.finalize_chat_task(task_id=task_id, response=response)
        response.evaluation_id = self._evaluation_service.evaluate_chat_result(
            task_id=task_id,
            contact_id=contact_id,
            request=chat_request,
            response=response,
        )
        self._record_audit(
            user_id=user_id,
            task_id=task_id,
            contact_id=contact_id,
            trace_id=runtime_task["trace_id"],
            selected_agent_id=selected_agent_id,
            route_payload=route_payload,
            message=message,
            summary=response.summary,
            outcome=1,
            started_at=started_at,
            references=response.references,
        )
        return AgentGatewayInvokeResult(
            task_id=task_id,
            contact_id=contact_id,
            selected_agent_id=selected_agent_id,
            selected_agent_name=profile.agent_name,
            matched_skill_ids=list(route_payload.get("matched_skill_ids") or []),
            route_reason=route_payload.get("route_reason") or "",
            policy_decision=route_payload.get("policy_decision") or "allow",
            declared_skills=list(bundle["skills"]),
            declared_mcps=list(bundle["mcps"]),
            declared_workflows=list(bundle["workflows"]),
            summary=response.summary,
            next_action=response.next_action,
            references=list(response.references or []),
            audit_tags=list(response.audit_tags or []),
            routing_trace=response.routing_trace,
            risk_flags=list(route_payload.get("risk_flags") or []),
        )

    def _emit_gateway_events(
        self,
        *,
        task_id: str,
        selected_agent_id: str,
        selected_agent_name: str,
        requested_agent_id: str | None,
        route_payload: dict,
        bundle: dict,
    ) -> None:
        self._task_service.emit_runtime_event(
            task_id=task_id,
            event_type="gateway_policy_checked",
            title="Gateway policy checked",
            content=route_payload.get("policy_decision") or "allow",
            agent_id=selected_agent_id,
            event_payload={
                "selected_agent_id": selected_agent_id,
                "selected_agent_name": selected_agent_name,
                "policy_decision": route_payload.get("policy_decision") or "allow",
                "filtered_candidates": list(route_payload.get("filtered_candidates") or []),
                "risk_flags": list(route_payload.get("risk_flags") or []),
            },
            current_stage="routing",
            task_status="running",
        )
        self._task_service.emit_runtime_event(
            task_id=task_id,
            event_type="agent_selected",
            title="Gateway selected child agent",
            content=selected_agent_name,
            agent_id=selected_agent_id,
            event_payload={
                "requested_agent_id": requested_agent_id,
                "capability_id": selected_agent_id,
                "capability_name": selected_agent_name,
                "route_reason": route_payload.get("route_reason") or "",
                "matched_skill_ids": list(route_payload.get("matched_skill_ids") or []),
                "candidate_agent_ids": list(route_payload.get("candidate_agent_ids") or []),
                "allowed_agent_ids": list(route_payload.get("allowed_agent_ids") or []),
                "ranked_candidates": list(route_payload.get("ranked_candidates") or []),
                "policy_decision": route_payload.get("policy_decision") or "allow",
            },
            current_stage="routing",
            task_status="running",
        )
        self._task_service.emit_runtime_event(
            task_id=task_id,
            event_type="gateway_declared_contract_loaded",
            title="Gateway loaded declared capabilities",
            content=(
                f"skills={len(bundle['skills'])}, "
                f"mcps={len(bundle['mcps'])}, "
                f"workflows={len(bundle['workflows'])}"
            ),
            agent_id=selected_agent_id,
            event_payload={
                "declared_skills": [
                    {"skill_id": item.skill_id, "skill_name": item.skill_name}
                    for item in bundle["skills"]
                ],
                "declared_mcps": [
                    {"mcp_id": item.mcp_id, "mcp_name": item.mcp_name}
                    for item in bundle["mcps"]
                ],
                "declared_workflows": [
                    {"workflow_id": item.workflow_id, "workflow_name": item.workflow_name}
                    for item in bundle["workflows"]
                ],
            },
            current_stage="executing",
            task_status="running",
        )

    def _record_audit(
        self,
        *,
        user_id: str,
        task_id: str,
        contact_id: str | None,
        trace_id: str,
        selected_agent_id: str,
        route_payload: dict,
        message: str,
        summary: str,
        outcome: int,
        started_at: datetime,
        references: list[str] | None = None,
        error_msg: str | None = None,
    ) -> None:
        finished_at = datetime.utcnow()
        duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
        self._audit_service.record(
            action="agent_gateway.invoke",
            actor_id=user_id,
            payload={
                "source": "agent_gateway",
                "event_type": "gateway_invoke",
                "outcome": outcome,
                "task_id": task_id,
                "trace_id": trace_id,
                "session_id": contact_id,
                "capability_id": selected_agent_id,
                "agent_id": selected_agent_id,
                "request_summary": message,
                "response_summary": summary,
                "error_msg": error_msg,
                "duration_ms": duration_ms,
                "request_time": started_at,
                "response_time": finished_at,
                "payload": {
                    "selected_agent_id": selected_agent_id,
                    "matched_skill_ids": list(route_payload.get("matched_skill_ids") or []),
                    "route_reason": route_payload.get("route_reason") or "",
                    "policy_decision": route_payload.get("policy_decision") or "allow",
                    "risk_flags": list(route_payload.get("risk_flags") or []),
                    "candidate_agent_ids": list(route_payload.get("candidate_agent_ids") or []),
                    "allowed_agent_ids": list(route_payload.get("allowed_agent_ids") or []),
                    "references": list(references or []),
                    "request_time": started_at.isoformat(),
                    "response_time": finished_at.isoformat(),
                    "duration_ms": duration_ms,
                },
            },
        )

    @staticmethod
    def _build_metadata(*, profile, bundle: dict) -> CapabilityMetadata:  # noqa: ANN001
        endpoint = profile.endpoint
        service_path = "/a2a" if (profile.transport or "a2a") == "a2a" else "/api/chat"
        if endpoint:
            parsed = urlparse(endpoint)
            if parsed.scheme and parsed.netloc:
                endpoint = f"{parsed.scheme}://{parsed.netloc}"
                if parsed.path and parsed.path != "/":
                    service_path = parsed.path
        return CapabilityMetadata(
            capability_id=profile.agent_id,
            capability_name=profile.agent_name,
            biz_domain=AgentGatewayExecutionService._parse_biz_domain(profile.biz_domain),
            description=profile.description or profile.agent_name,
            priority=1,
            triggers=[],
            skills=[item.skill_id for item in bundle["skills"]],
            version=profile.version,
            risk_level=profile.risk_level,
            requires_approval=False,
            tags=list(profile.tags or []),
            transport=profile.transport or "a2a",
            endpoint=endpoint,
            service_path=service_path,
            extras={"source": profile.source},
            source=profile.source,
        )

    @staticmethod
    def _parse_biz_domain(value: str) -> BizDomain:
        try:
            return BizDomain(value)
        except ValueError as exc:
            raise ValueError(f"unsupported biz_domain: {value}") from exc
