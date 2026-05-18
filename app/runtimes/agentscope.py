from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.agents.base import CapabilityAgent
from app.config import Settings
from app.runtimes.base import RuntimeContext
from app.schemas import ChatRequest, ChatResponse
from app.services.observation_service import ObservationService
from app.services.skill_registry import SkillRegistry, SkillRuntimeSpec
from app.services.tool_execution_service import ToolExecutionService
from app.tools import ToolSpec, list_tool_specs


@dataclass(frozen=True)
class AgentScopeRuntimeSession:
    session_id: str
    runtime_name: str
    capability_id: str
    capability_name: str
    task_id: str
    contact_id: str
    trace_id: str
    framework_available: bool
    framework_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentScopeExecutionStep:
    step_id: str
    step_type: str
    title: str
    content: str = ""
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentScopeExecutionPlan:
    session_id: str
    capability_id: str
    capability_name: str
    selected_skill_ids: list[str] = field(default_factory=list)
    loaded_skill_ids: list[str] = field(default_factory=list)
    tool_inventory_ids: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    system_prompt: str = ""
    steps: list[AgentScopeExecutionStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentScopePlannerResult:
    session_id: str
    planning_summary: str
    planned_tool_ids: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    escalation_reasons: list[str] = field(default_factory=list)
    step_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentScopeExecutorResult:
    session_id: str
    execution_summary: str
    selected_skill_ids: list[str] = field(default_factory=list)
    selected_tool_ids: list[str] = field(default_factory=list)
    requires_approval: bool = False
    framework_available: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentScopeBridgeResult:
    bridge_mode: str
    bridge_summary: str
    framework_reason: str = ""
    response_summary: str = ""
    response_next_action: str = ""
    selected_tool_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentScopeAgentRuntime:
    """Phase 2 AgentScope runtime foundation.

    This runtime keeps Phase 1 capability agents executable while promoting the
    AgentScope boundary into a real orchestration layer that prepares:
    - runtime session metadata
    - structured skill bundle
    - filtered tool inventory
    - execution plan for frontend/audit visibility

    The actual business answer still comes from the existing capability agent.
    A later step can replace that final execution with true AgentScope session,
    memory, model, and tool orchestration.
    """

    runtime_name = "agentscope"
    _framework_bootstrapped = False

    def __init__(
        self,
        skill_registry: SkillRegistry | None = None,
        settings: Settings | None = None,
        tool_execution_service: ToolExecutionService | None = None,
        observation_service: ObservationService | None = None,
    ) -> None:
        self._skill_registry = skill_registry
        self._settings = settings or Settings()
        self._tool_execution_service = tool_execution_service or ToolExecutionService()
        self._observation_service = observation_service

    def run(
        self,
        agent: CapabilityAgent,
        request: ChatRequest,
        context: RuntimeContext,
    ) -> ChatResponse:
        run_started_at = datetime.utcnow()
        framework = self._detect_framework()
        session = self._build_session(agent=agent, context=context, framework=framework)
        context.metadata["request_message"] = request.message

        runtime_skills = self._load_runtime_skills(context.skill_ids)
        tool_inventory = self._resolve_tool_inventory(
            request=request,
            runtime_skills=runtime_skills,
        )
        execution_plan = self._build_execution_plan(
            session=session,
            agent=agent,
            request=request,
            runtime_skills=runtime_skills,
            tool_inventory=tool_inventory,
        )
        planner_result = self._run_planner(
            session=session,
            execution_plan=execution_plan,
            runtime_skills=runtime_skills,
        )
        planner_finished_at = datetime.utcnow()
        self._record_observation(
            task_id=context.task_id,
            trace_id=context.trace_id,
            session_id=session.session_id,
            agent_id=agent.definition.capability_id,
            call_type="runtime",
            phase="planner",
            status="success",
            input_snapshot=request.message,
            output_snapshot=planner_result.planning_summary,
            extra_info={
                "selected_skill_ids": execution_plan.selected_skill_ids,
                "loaded_skill_ids": execution_plan.loaded_skill_ids,
                "tool_inventory_ids": execution_plan.tool_inventory_ids,
                "required_inputs": execution_plan.required_inputs,
                "step_count": planner_result.step_count,
            },
            start_time=run_started_at,
            end_time=planner_finished_at,
        )

        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="agent_selected",
            title="已选择业务 Agent",
            content=agent.definition.name,
            agent_id=agent.definition.capability_id,
            event_payload={
                "capability_id": agent.definition.capability_id,
                "skills": context.skill_ids,
                "runtime_session_id": session.session_id,
            },
            current_stage="routing",
            task_status="running",
        )
        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="agent_started",
            title="Agent 开始执行",
            content=request.message,
            agent_id=agent.definition.capability_id,
            event_payload={
                "runtime": self.runtime_name,
                "runtime_session_id": session.session_id,
                "framework_available": session.framework_available,
                "framework_version": session.framework_version,
            },
            current_stage="executing",
            task_status="running",
        )
        self._emit_runtime_preparation_events(
            context=context,
            session=session,
            runtime_skills=runtime_skills,
            tool_inventory=tool_inventory,
            execution_plan=execution_plan,
            planner_result=planner_result,
        )

        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="executor_started",
            title="Executor started",
            content=planner_result.planning_summary,
            agent_id=agent.definition.capability_id,
            event_payload={
                "runtime_session_id": session.session_id,
                "planned_tool_ids": planner_result.planned_tool_ids,
                "missing_inputs": planner_result.missing_inputs,
            },
            current_stage="executing",
        )
        response, bridge_result = self._execute_with_bridge(
            agent=agent,
            request=request,
            session=session,
            execution_plan=execution_plan,
            tool_inventory=tool_inventory,
            context=context,
        )
        response.audit_tags.append(f"runtime:{self.runtime_name}")
        response.audit_tags.append(f"runtime_session:{session.session_id}")
        response.audit_tags.append(f"executor_bridge:{bridge_result.bridge_mode}")
        if bridge_result.framework_reason:
            response.audit_tags.append(f"executor_bridge_reason:{bridge_result.framework_reason}")
        if bridge_result.bridge_mode != "agentscope_react":
            response.audit_tags.append("runtime_fallback:local")

        executor_result = self._run_executor(
            session=session,
            response=response,
            bridge_result=bridge_result,
        )
        executor_finished_at = datetime.utcnow()
        self._record_observation(
            task_id=context.task_id,
            trace_id=context.trace_id,
            session_id=session.session_id,
            agent_id=agent.definition.capability_id,
            call_type="runtime",
            phase="bridge",
            model_provider="openai"
            if bridge_result.bridge_mode == "agentscope_react"
            else None,
            model_name=self._settings.agentscope_model_name or None,
            status="success" if bridge_result.bridge_mode == "agentscope_react" else "fallback",
            fallback_used=bridge_result.bridge_mode != "agentscope_react",
            fallback_reason=bridge_result.framework_reason or None,
            input_snapshot=request.message,
            output_snapshot=bridge_result.bridge_summary,
            extra_info={
                "bridge_mode": bridge_result.bridge_mode,
                "selected_tool_ids": bridge_result.selected_tool_ids,
                "response_summary": bridge_result.response_summary,
                "response_next_action": bridge_result.response_next_action,
            },
            start_time=planner_finished_at,
            end_time=executor_finished_at,
        )
        self._record_observation(
            task_id=context.task_id,
            trace_id=context.trace_id,
            session_id=session.session_id,
            agent_id=agent.definition.capability_id,
            call_type="runtime",
            phase="executor",
            model_provider="openai"
            if bridge_result.bridge_mode == "agentscope_react"
            else None,
            model_name=self._settings.agentscope_model_name or None,
            status="success",
            fallback_used=bridge_result.bridge_mode != "agentscope_react",
            fallback_reason=bridge_result.framework_reason or None,
            input_snapshot=request.message,
            output_snapshot=response.summary,
            extra_info={
                "selected_skills": response.selected_skills,
                "selected_tools": response.selected_tools,
                "requires_approval": response.requires_approval,
                "workflow": response.workflow,
                "reference_count": len(response.references),
            },
            start_time=planner_finished_at,
            end_time=executor_finished_at,
        )

        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="thought_generated",
            title="Agent 已生成阶段结果",
            content=response.next_action,
            agent_id=agent.definition.capability_id,
            event_payload={
                "runtime_session_id": session.session_id,
                "selected_tools": response.selected_tools,
                "selected_skills": response.selected_skills,
                "framework_available": session.framework_available,
            },
            current_stage="executing",
        )
        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="executor_completed",
            title="Executor completed",
            content=executor_result.execution_summary,
            agent_id=agent.definition.capability_id,
            event_payload=asdict(executor_result),
            current_stage="executing",
        )
        return response

    def _record_observation(
        self,
        *,
        task_id: str,
        trace_id: str,
        session_id: str | None,
        agent_id: str | None,
        call_type: str,
        phase: str | None,
        status: str,
        input_snapshot: str,
        output_snapshot: str,
        extra_info: dict[str, Any] | None,
        start_time: datetime,
        end_time: datetime,
        model_provider: str | None = None,
        model_name: str | None = None,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
    ) -> None:
        if self._observation_service is None:
            return
        latency_ms = max(0, int((end_time - start_time).total_seconds() * 1000))
        self._observation_service.record_observation(
            task_id=task_id,
            trace_id=trace_id,
            session_id=session_id,
            agent_id=agent_id,
            runtime_name=self.runtime_name,
            call_type=call_type,
            phase=phase,
            model_provider=model_provider,
            model_name=model_name,
            status=status,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            input_snapshot=input_snapshot,
            output_snapshot=output_snapshot,
            extra_info=extra_info,
            latency_ms=latency_ms,
            start_time=start_time,
            end_time=end_time,
        )

    def _load_runtime_skills(self, skill_ids: list[str]) -> list[SkillRuntimeSpec]:
        if self._skill_registry is None:
            return []
        return self._skill_registry.load_runtime_skills(skill_ids)

    def _resolve_tool_inventory(
        self,
        *,
        request: ChatRequest,
        runtime_skills: list[SkillRuntimeSpec],
    ) -> list[ToolSpec]:
        tool_specs = list_tool_specs(request.biz_domain)
        allowed_tool_ids = {
            tool_id
            for skill in runtime_skills
            for tool_id in skill.allowed_tools
            if tool_id
        }
        if not allowed_tool_ids:
            return tool_specs
        return [item for item in tool_specs if item.tool_id in allowed_tool_ids]

    def _build_session(
        self,
        *,
        agent: CapabilityAgent,
        context: RuntimeContext,
        framework: dict[str, Any],
    ) -> AgentScopeRuntimeSession:
        return AgentScopeRuntimeSession(
            session_id=f"rt_{uuid4().hex[:24]}",
            runtime_name=self.runtime_name,
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            task_id=context.task_id,
            contact_id=context.contact_id,
            trace_id=context.trace_id,
            framework_available=framework["available"],
            framework_version=framework["version"],
            metadata=dict(context.metadata),
        )

    def _build_execution_plan(
        self,
        *,
        session: AgentScopeRuntimeSession,
        agent: CapabilityAgent,
        request: ChatRequest,
        runtime_skills: list[SkillRuntimeSpec],
        tool_inventory: list[ToolSpec],
    ) -> AgentScopeExecutionPlan:
        required_inputs = self._merge_required_inputs(runtime_skills)
        system_prompt = self._render_system_prompt(
            agent=agent,
            runtime_skills=runtime_skills,
            tool_inventory=tool_inventory,
        )
        steps = self._build_steps(
            request=request,
            runtime_skills=runtime_skills,
            tool_inventory=tool_inventory,
        )
        return AgentScopeExecutionPlan(
            session_id=session.session_id,
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            selected_skill_ids=list(agent.definition.skills),
            loaded_skill_ids=[item.skill_id for item in runtime_skills],
            tool_inventory_ids=[item.tool_id for item in tool_inventory],
            required_inputs=required_inputs,
            system_prompt=system_prompt,
            steps=steps,
            metadata={
                "framework_available": session.framework_available,
                "framework_version": session.framework_version,
                "user_message": request.message,
            },
        )

    def _build_steps(
        self,
        *,
        request: ChatRequest,
        runtime_skills: list[SkillRuntimeSpec],
        tool_inventory: list[ToolSpec],
    ) -> list[AgentScopeExecutionStep]:
        steps = [
            AgentScopeExecutionStep(
                step_id="analyze_request",
                step_type="analysis",
                title="Analyze request",
                content=request.message,
                metadata={"biz_domain": request.biz_domain.value},
            )
        ]
        for skill in runtime_skills:
            steps.append(
                AgentScopeExecutionStep(
                    step_id=f"skill_{skill.skill_id}",
                    step_type="skill",
                    title=f"Load skill {skill.skill_id}",
                    content=skill.purpose,
                    metadata={
                        "required_inputs": list(skill.required_inputs),
                        "allowed_tools": list(skill.allowed_tools),
                        "step_count": len(skill.steps),
                    },
                )
            )
        if tool_inventory:
            steps.append(
                AgentScopeExecutionStep(
                    step_id="prepare_tools",
                    step_type="tooling",
                    title="Prepare tool inventory",
                    content=", ".join(item.tool_id for item in tool_inventory),
                    metadata={"tool_count": len(tool_inventory)},
                )
            )
        steps.append(
            AgentScopeExecutionStep(
                step_id="execute_capability",
                step_type="execution",
                title="Execute capability agent",
                content="Run current capability implementation and emit task artifacts.",
            )
        )
        return steps

    def _render_system_prompt(
        self,
        *,
        agent: CapabilityAgent,
        runtime_skills: list[SkillRuntimeSpec],
        tool_inventory: list[ToolSpec],
    ) -> str:
        sections = [
            f"Capability: {agent.definition.name}",
            f"Capability ID: {agent.definition.capability_id}",
            f"Domain: {agent.definition.biz_domain.value}",
            f"Description: {agent.definition.description}",
        ]
        if runtime_skills:
            sections.append("Skills:")
            for skill in runtime_skills:
                sections.append(f"- {skill.skill_id}: {skill.purpose}")
                if skill.steps:
                    sections.append(f"  Steps: {' | '.join(skill.steps)}")
                if skill.human_escalation:
                    sections.append(
                        f"  Escalation: {' | '.join(skill.human_escalation)}"
                    )
        if tool_inventory:
            sections.append("Tool Inventory:")
            for tool in tool_inventory:
                sections.append(
                    f"- {tool.tool_id} ({tool.tool_type}, provider={tool.provider})"
                )
        return "\n".join(sections)

    def _merge_required_inputs(
        self,
        runtime_skills: list[SkillRuntimeSpec],
    ) -> list[str]:
        merged: list[str] = []
        for skill in runtime_skills:
            for item in skill.required_inputs:
                if item not in merged:
                    merged.append(item)
        return merged

    def _emit_runtime_preparation_events(
        self,
        *,
        context: RuntimeContext,
        session: AgentScopeRuntimeSession,
        runtime_skills: list[SkillRuntimeSpec],
        tool_inventory: list[ToolSpec],
        execution_plan: AgentScopeExecutionPlan,
        planner_result: AgentScopePlannerResult,
    ) -> None:
        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="runtime_session_started",
            title="Runtime session started",
            content=session.session_id,
            agent_id=session.capability_id,
            event_payload=asdict(session),
            current_stage="preparing",
        )

        if runtime_skills:
            self._emit_event(
                context=context,
                task_id=context.task_id,
                event_type="skill_bundle_loaded",
                title="Skill bundle loaded",
                content=", ".join(item.skill_id for item in runtime_skills),
                agent_id=session.capability_id,
                event_payload={
                    "runtime_session_id": session.session_id,
                    "skills": [
                        {
                            "skill_id": item.skill_id,
                            "purpose": item.purpose,
                            "required_inputs": item.required_inputs,
                            "allowed_tools": item.allowed_tools,
                        }
                        for item in runtime_skills
                    ],
                },
                current_stage="preparing",
            )

        if tool_inventory:
            self._emit_event(
                context=context,
                task_id=context.task_id,
                event_type="tool_inventory_prepared",
                title="Tool inventory prepared",
                content=", ".join(item.tool_id for item in tool_inventory),
                agent_id=session.capability_id,
                event_payload={
                    "runtime_session_id": session.session_id,
                    "tools": [asdict(item) for item in tool_inventory],
                },
                current_stage="preparing",
            )

        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="planner_started",
            title="Planner started",
            content=session.capability_name,
            agent_id=session.capability_id,
            event_payload={
                "runtime_session_id": session.session_id,
                "selected_skill_ids": execution_plan.selected_skill_ids,
                "tool_inventory_ids": execution_plan.tool_inventory_ids,
            },
            current_stage="planning",
        )
        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="execution_plan_created",
            title="Execution plan created",
            content=f"{len(execution_plan.steps)} planned steps",
            agent_id=session.capability_id,
            event_payload={
                "runtime_session_id": session.session_id,
                "required_inputs": execution_plan.required_inputs,
                "selected_skill_ids": execution_plan.selected_skill_ids,
                "loaded_skill_ids": execution_plan.loaded_skill_ids,
                "tool_inventory_ids": execution_plan.tool_inventory_ids,
                "system_prompt_preview": execution_plan.system_prompt[:800],
                "steps": [asdict(item) for item in execution_plan.steps],
            },
            current_stage="planning",
        )
        self._emit_event(
            context=context,
            task_id=context.task_id,
            event_type="planner_completed",
            title="Planner completed",
            content=planner_result.planning_summary,
            agent_id=session.capability_id,
            event_payload=asdict(planner_result),
            current_stage="planning",
        )

        if not session.framework_available:
            self._emit_event(
                context=context,
                task_id=context.task_id,
                event_type="runtime_fallback",
                title="Runtime fallback",
                content="AgentScope package not installed, using local capability execution path.",
                agent_id=session.capability_id,
                event_payload={
                    "runtime_session_id": session.session_id,
                    "fallback": "local_capability_agent",
                },
                current_stage="planning",
            )

    def _run_planner(
        self,
        *,
        session: AgentScopeRuntimeSession,
        execution_plan: AgentScopeExecutionPlan,
        runtime_skills: list[SkillRuntimeSpec],
    ) -> AgentScopePlannerResult:
        escalation_reasons = self._merge_human_escalation(runtime_skills)
        planning_summary = (
            f"Planner prepared {len(execution_plan.steps)} steps, "
            f"{len(execution_plan.tool_inventory_ids)} tools, "
            f"and {len(execution_plan.required_inputs)} required inputs."
        )
        return AgentScopePlannerResult(
            session_id=session.session_id,
            planning_summary=planning_summary,
            planned_tool_ids=list(execution_plan.tool_inventory_ids),
            missing_inputs=list(execution_plan.required_inputs),
            escalation_reasons=escalation_reasons,
            step_count=len(execution_plan.steps),
            metadata={
                "framework_available": session.framework_available,
                "framework_version": session.framework_version,
            },
        )

    def _run_executor(
        self,
        *,
        session: AgentScopeRuntimeSession,
        response: ChatResponse,
        bridge_result: AgentScopeBridgeResult,
    ) -> AgentScopeExecutorResult:
        execution_summary = (
            f"Executor finished in mode={bridge_result.bridge_mode} with "
            f"{len(response.selected_tools)} tools and "
            f"approval_required={response.requires_approval}."
        )
        return AgentScopeExecutorResult(
            session_id=session.session_id,
            execution_summary=execution_summary,
            selected_skill_ids=list(response.selected_skills),
            selected_tool_ids=list(response.selected_tools),
            requires_approval=response.requires_approval,
            framework_available=session.framework_available,
            metadata={
                "bridge_mode": bridge_result.bridge_mode,
                "bridge_summary": bridge_result.bridge_summary,
                "framework_reason": bridge_result.framework_reason,
                "workflow": response.workflow,
                "reference_count": len(response.references),
            },
        )

    def _execute_with_bridge(
        self,
        *,
        agent: CapabilityAgent,
        request: ChatRequest,
        session: AgentScopeRuntimeSession,
        execution_plan: AgentScopeExecutionPlan,
        tool_inventory: list[ToolSpec],
        context: RuntimeContext,
    ) -> tuple[ChatResponse, AgentScopeBridgeResult]:
        framework_response, bridge_result = self._try_agentscope_framework_execution(
            agent=agent,
            request=request,
            session=session,
            execution_plan=execution_plan,
            tool_inventory=tool_inventory,
            context=context,
        )
        baseline_response = agent.run(request)
        if framework_response is None:
            return baseline_response, bridge_result

        baseline_response.summary = framework_response.get("summary", baseline_response.summary)
        baseline_response.next_action = framework_response.get(
            "next_action",
            baseline_response.next_action,
        )
        bridge_tools = framework_response.get("selected_tools", [])
        if bridge_tools:
            merged_tools = list(dict.fromkeys(list(baseline_response.selected_tools) + bridge_tools))
            baseline_response.selected_tools = merged_tools
        bridge_tool_results = framework_response.get("tool_results", [])
        if bridge_tool_results:
            baseline_response.runtime_tool_results = bridge_tool_results
        return baseline_response, bridge_result

    def _try_agentscope_framework_execution(
        self,
        *,
        agent: CapabilityAgent,
        request: ChatRequest,
        session: AgentScopeRuntimeSession,
        execution_plan: AgentScopeExecutionPlan,
        tool_inventory: list[ToolSpec],
        context: RuntimeContext,
    ) -> tuple[dict[str, Any] | None, AgentScopeBridgeResult]:
        if not session.framework_available:
            return None, AgentScopeBridgeResult(
                bridge_mode="local_capability",
                bridge_summary="AgentScope package unavailable, local capability execution used.",
                framework_reason="framework_unavailable",
            )
        if not self._settings.agentscope_use_model_bridge:
            return None, AgentScopeBridgeResult(
                bridge_mode="local_capability",
                bridge_summary="AgentScope model bridge disabled, local capability execution used.",
                framework_reason="bridge_disabled",
            )
        if not self._settings.agentscope_model_name:
            return None, AgentScopeBridgeResult(
                bridge_mode="local_capability",
                bridge_summary="AgentScope model name missing, local capability execution used.",
                framework_reason="model_name_missing",
            )

        try:
            import agentscope
            from agentscope.agent import ReActAgent
            from agentscope.formatter import OpenAIChatFormatter
            from agentscope.message import Msg
            from agentscope.model import OpenAIChatModel
            from agentscope.tool import ToolResponse, Toolkit
        except Exception as exc:  # noqa: BLE001
            return None, AgentScopeBridgeResult(
                bridge_mode="local_capability",
                bridge_summary="AgentScope runtime bridge import failed, local capability execution used.",
                framework_reason=f"bridge_import_failed:{type(exc).__name__}",
            )

        try:
            if not AgentScopeAgentRuntime._framework_bootstrapped:
                agentscope.init(
                    project="jagent",
                    name=agent.definition.capability_id,
                    run_id=session.session_id,
                )
                AgentScopeAgentRuntime._framework_bootstrapped = True

            toolkit = Toolkit(agent_skill_instruction=execution_plan.system_prompt)
            tool_results: list[dict[str, Any]] = []
            for tool_spec in tool_inventory:
                tool_func, func_name = self._build_framework_tool_function(
                    tool_spec=tool_spec,
                    session=session,
                    context=context,
                    capability_id=agent.definition.capability_id,
                    request_message=request.message,
                    tool_results=tool_results,
                )
                toolkit.register_tool_function(
                    tool_func,
                    func_name=func_name,
                    func_description=tool_spec.description
                    or f"Business tool bridge for {tool_spec.tool_id}",
                    include_var_keyword=True,
                    namesake_strategy="rename",
                )

            client_kwargs: dict[str, Any] | None = None
            if self._settings.agentscope_base_url:
                client_kwargs = {"base_url": self._settings.agentscope_base_url}

            model = OpenAIChatModel(
                model_name=self._settings.agentscope_model_name,
                api_key=self._settings.agentscope_api_key or None,
                client_kwargs=client_kwargs,
                stream=False,
            )
            formatter = OpenAIChatFormatter()
            react_agent = ReActAgent(
                name=agent.definition.name,
                sys_prompt=execution_plan.system_prompt,
                model=model,
                formatter=formatter,
                toolkit=toolkit,
                max_iters=self._settings.agentscope_max_iters,
            )
            msg = react_agent.reply(
                Msg(
                    name="user",
                    role="user",
                    content=request.message,
                    metadata={
                        "task_id": session.task_id,
                        "trace_id": session.trace_id,
                        "biz_domain": agent.definition.biz_domain.value,
                    },
                )
            )
            text = self._extract_message_text(msg)
            summary, next_action = self._split_framework_text(text)
            return (
                {
                    "summary": summary,
                    "next_action": next_action,
                    "selected_tools": [
                        item["tool_id"] for item in tool_results if item.get("tool_id")
                    ],
                    "tool_results": tool_results,
                },
                AgentScopeBridgeResult(
                    bridge_mode="agentscope_react",
                    bridge_summary="AgentScope ReAct executor completed.",
                    response_summary=summary,
                    response_next_action=next_action,
                    selected_tool_ids=[
                        item["tool_id"] for item in tool_results if item.get("tool_id")
                    ],
                    metadata={
                        "framework_version": session.framework_version,
                        "tool_count": len(tool_inventory),
                    },
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return None, AgentScopeBridgeResult(
                bridge_mode="local_capability",
                bridge_summary="AgentScope executor failed, local capability execution used.",
                framework_reason=f"bridge_execution_failed:{type(exc).__name__}",
            )

    @staticmethod
    def _detect_framework() -> dict[str, Any]:
        try:
            import agentscope  # noqa: F401
        except ImportError:
            return {"available": False, "version": "unavailable"}

        return {
            "available": True,
            "version": getattr(agentscope, "__version__", "unknown"),
        }

    @staticmethod
    def _emit_event(
        *,
        context: RuntimeContext,
        task_id: str,
        event_type: str,
        title: str,
        content: str,
        agent_id: str | None = None,
        event_payload: dict[str, Any] | None = None,
        current_stage: str | None = None,
        task_status: str | None = None,
    ) -> None:
        if not context.emit_event or not task_id:
            return
        context.emit_event(
            task_id=task_id,
            event_type=event_type,
            title=title,
            content=content,
            agent_id=agent_id,
            event_payload=event_payload or {},
            current_stage=current_stage,
            task_status=task_status,
        )

    @staticmethod
    def _merge_human_escalation(
        runtime_skills: list[SkillRuntimeSpec],
    ) -> list[str]:
        merged: list[str] = []
        for skill in runtime_skills:
            for item in skill.human_escalation:
                if item not in merged:
                    merged.append(item)
        return merged

    def _build_framework_tool_function(
        self,
        *,
        tool_spec: ToolSpec,
        session: AgentScopeRuntimeSession,
        context: RuntimeContext,
        capability_id: str,
        request_message: str,
        tool_results: list[dict[str, Any]],
    ) -> tuple[Any, str]:
        safe_name = tool_spec.tool_id.replace("-", "_")

        def tool_bridge(query: str = "", **kwargs: Any):  # noqa: ANN202
            """Execute platform tools through the unified tool execution service."""

            from agentscope.tool import ToolResponse

            result = self._tool_execution_service.execute_tool(
                tool_id=tool_spec.tool_id,
                request_context={
                    "task_id": session.task_id,
                    "contact_id": session.contact_id,
                    "trace_id": session.trace_id,
                    "runtime_session_id": session.session_id,
                    "request_message": request_message,
                    "query": query,
                    "kwargs": kwargs,
                },
                emit_event=context.emit_event,
                agent_id=capability_id,
                current_stage="executing",
            )
            tool_results.append(result.to_event_payload())
            return ToolResponse(
                content=[
                    {
                        "type": "text",
                        "text": result.output_summary,
                    }
                ],
                metadata=result.to_event_payload(),
            )

        tool_bridge.__name__ = safe_name
        return tool_bridge, safe_name

    @staticmethod
    def _extract_message_text(msg: Any) -> str:
        content = getattr(msg, "content", msg)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                else:
                    parts.append(str(item))
            return "\n".join(parts).strip()
        return str(content)

    @staticmethod
    def _split_framework_text(text: str) -> tuple[str, str]:
        cleaned = " ".join(text.split()).strip()
        if not cleaned:
            return "Framework executor returned empty content.", "Fallback to local capability guidance."
        if len(cleaned) <= 160:
            return cleaned, cleaned
        summary = cleaned[:160].rstrip()
        next_action = cleaned[160:320].rstrip() or summary
        return summary, next_action
