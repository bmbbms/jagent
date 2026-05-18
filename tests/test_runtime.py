from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.base import CapabilityAgent, CapabilityDefinition
from app.db.base import Base
from app.repositories.observation_repository import ObservationRepository
from app.registry.base import CapabilityMetadata, CapabilityRoutePlan
from app.runtimes.agentscope import AgentScopeAgentRuntime
from app.runtimes.base import RuntimeContext
from app.schemas import BizDomain, ChatRequest, ChatResponse
from app.services.observation_service import ObservationService
from app.services.skill_registry import SkillRegistry


class DummyMerchantAgent(CapabilityAgent):
    definition = CapabilityDefinition(
        capability_id="merchant.qa",
        name="Merchant QA Agent",
        biz_domain=BizDomain.merchant,
        description="dummy merchant qa",
        skills=["merchant_qa"],
        priority=10,
    )

    def run(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            domain=BizDomain.merchant,
            capability_id=self.definition.capability_id,
            capability_name=self.definition.name,
            summary="ok",
            next_action="next",
            selected_skills=["merchant_qa"],
            selected_tools=["merchant_profile_query"],
            references=["K001"],
            requires_approval=False,
            workflow=None,
            audit_tags=[],
        )


def test_agentscope_runtime_emits_planner_executor_events() -> None:
    registry = SkillRegistry.from_directory("app/skills")
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    observation_service = ObservationService(
        session_factory=session_factory,
        repository=ObservationRepository(),
    )
    runtime = AgentScopeAgentRuntime(
        skill_registry=registry,
        observation_service=observation_service,
    )
    agent = DummyMerchantAgent()
    request = ChatRequest(user_id="u-runtime", biz_domain=BizDomain.merchant, message="faq")

    captured_events: list[dict] = []

    def emit_event(**payload):
        captured_events.append(payload)
        return {"event_id": f"evt_{len(captured_events)}", "event_seq": len(captured_events)}

    route_plan = CapabilityRoutePlan(
        selected=CapabilityMetadata(
            capability_id=agent.definition.capability_id,
            capability_name=agent.definition.name,
            biz_domain=agent.definition.biz_domain,
            description=agent.definition.description,
            priority=agent.definition.priority,
            triggers=agent.definition.triggers,
            skills=agent.definition.skills,
        ),
        selected_agent=agent,
    )

    response = runtime.run(
        agent,
        request,
        RuntimeContext(
            route_plan=route_plan,
            task_id="task_runtime",
            contact_id="ct_runtime",
            trace_id="trace_runtime",
            skill_ids=agent.definition.skills,
            emit_event=emit_event,
        ),
    )

    assert response.capability_id == "merchant.qa"
    assert any(tag.startswith("runtime_session:") for tag in response.audit_tags)
    assert "executor_bridge:local_capability" in response.audit_tags

    event_types = [item["event_type"] for item in captured_events]
    for required in [
        "runtime_session_started",
        "skill_bundle_loaded",
        "tool_inventory_prepared",
        "planner_started",
        "execution_plan_created",
        "planner_completed",
        "executor_started",
        "thought_generated",
        "executor_completed",
    ]:
        assert required in event_types

    executor_completed = next(
        item for item in captured_events if item["event_type"] == "executor_completed"
    )
    assert executor_completed["event_payload"]["metadata"]["bridge_mode"] == "local_capability"

    observations = observation_service.list_observations(task_id="task_runtime")
    assert len(observations) == 3
    phases = [item.phase for item in observations]
    assert phases == ["planner", "bridge", "executor"]
    assert observations[1].status == "fallback"
    assert observations[1].fallback_used is True
