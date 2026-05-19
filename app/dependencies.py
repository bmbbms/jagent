from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.agents.loader import load_capability_modules
from app.agents.router import RouterAgent
from app.config import get_settings
from app.db.init_db import init_db, run_db_migrations
from app.db.session import create_db_engine, create_session_factory
from app.registry.bootstrap import set_active_registrar
from app.registry.composite_registry import CompositeCapabilityRegistry
from app.registry.local_registry import LocalCapabilityRegistry
from app.registry.manual_remote_registry import ManualRemoteCapabilityRegistry
from app.registry.nacos_registry import NacosCapabilityRegistry
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.external_capability_repository import ExternalCapabilityRepository
from app.repositories.observation_repository import ObservationRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.runtimes.agentscope import AgentScopeAgentRuntime
from app.runtimes.base import AgentRuntime
from app.runtimes.local import LocalAgentRuntime
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService
from app.services.evaluation_service import EvaluationService
from app.services.external_capability_persistence_service import (
    ExternalCapabilityPersistenceService,
)
from app.services.external_agent_health_service import ExternalAgentHealthService
from app.services.external_agent_discovery import ExternalAgentDiscoveryService
from app.services.internal_tool_registry import build_default_internal_tool_registry
from app.services.internal_tool_http_provider import HttpInternalToolProvider
from app.services.internal_tool_provider import InternalToolProvider, LocalDbInternalToolProvider
from app.services.knowledge_service import KnowledgeService
from app.services.mcp_service import MCPService
from app.services.observation_service import ObservationService
from app.services.skill_registry import SkillRegistry
from app.services.task_service import TaskService
from app.services.tool_execution_service import ToolExecutionService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.services.workflow_service import WorkflowService
from app.workflows import WorkflowRegistry


@lru_cache
def get_engine():
    settings = get_settings()
    engine = create_db_engine(settings)
    if settings.database_run_migrations:
        run_db_migrations(settings)
    elif settings.database_auto_create:
        init_db(engine)
    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


@lru_cache
def get_manual_remote_registry() -> ManualRemoteCapabilityRegistry:
    return ManualRemoteCapabilityRegistry()


@lru_cache
def get_capability_registry() -> CompositeCapabilityRegistry:
    settings = get_settings()
    local_registry = LocalCapabilityRegistry()
    secondary_registries = [
        get_manual_remote_registry(),
        NacosCapabilityRegistry(
            server_address=settings.nacos_server_address,
            namespace=settings.nacos_namespace,
            group=settings.nacos_group,
            service_prefix=settings.nacos_service_prefix,
            enabled=settings.nacos_enabled,
            service_host=settings.nacos_service_host,
            service_port=settings.nacos_service_port,
            service_path=settings.nacos_service_path,
            service_cluster=settings.nacos_service_cluster,
            service_weight=settings.nacos_service_weight,
        )
    ]

    registry = CompositeCapabilityRegistry(
        local_registry=local_registry,
        secondary_registries=secondary_registries,
    )
    set_active_registrar(registry)

    load_capability_modules(settings.capability_module_packages)

    return registry


@lru_cache
def get_router_agent() -> RouterAgent:
    return RouterAgent(
        capability_resolver=get_capability_registry(),
        runtime=get_agent_runtime(),
    )


@lru_cache
def get_agent_runtime() -> AgentRuntime:
    settings = get_settings()
    if settings.agent_runtime == "agentscope":
        return AgentScopeAgentRuntime(
            skill_registry=get_skill_registry(),
            settings=settings,
            tool_execution_service=get_tool_execution_service(),
            observation_service=get_observation_service(),
        )
    return LocalAgentRuntime()


@lru_cache
def get_approval_service() -> ApprovalService:
    service = ApprovalService(
        session_factory=get_session_factory(),
        repository=ApprovalRepository(),
    )
    service.seed_if_needed()
    return service


@lru_cache
def get_audit_service() -> AuditService:
    return AuditService(
        session_factory=get_session_factory(),
        repository=AuditRepository(),
    )


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(
        session_factory=get_session_factory(),
        repository=ChatRepository(),
    )


@lru_cache
def get_task_service() -> TaskService:
    return TaskService(
        session_factory=get_session_factory(),
        repository=TaskRepository(),
        mcp_service=get_mcp_service(),
        tool_execution_service=get_tool_execution_service(),
        tool_execution_log_service=get_tool_execution_log_service(),
        observation_service=get_observation_service(),
    )


@lru_cache
def get_evaluation_service() -> EvaluationService:
    return EvaluationService(
        session_factory=get_session_factory(),
        repository=EvaluationRepository(),
        observation_service=get_observation_service(),
        tool_execution_log_service=get_tool_execution_log_service(),
    )


@lru_cache
def get_external_agent_discovery_service() -> ExternalAgentDiscoveryService:
    return ExternalAgentDiscoveryService()


@lru_cache
def get_external_capability_persistence_service() -> ExternalCapabilityPersistenceService:
    return ExternalCapabilityPersistenceService(
        session_factory=get_session_factory(),
        repository=ExternalCapabilityRepository(),
        registry=get_manual_remote_registry(),
    )


@lru_cache
def get_external_agent_health_service() -> ExternalAgentHealthService:
    return ExternalAgentHealthService(
        persistence_service=get_external_capability_persistence_service(),
    )


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService()


@lru_cache
def get_mcp_service() -> MCPService:
    return MCPService()


@lru_cache
def get_tool_execution_service() -> ToolExecutionService:
    return ToolExecutionService(
        mcp_service=get_mcp_service(),
        internal_tool_registry=build_default_internal_tool_registry(get_internal_tool_provider()),
        log_service=get_tool_execution_log_service(),
    )


@lru_cache
def get_internal_tool_provider() -> InternalToolProvider:
    settings = get_settings()
    if settings.internal_tool_provider_backend == "local_db":
        return LocalDbInternalToolProvider(get_session_factory())
    if settings.internal_tool_provider_backend == "http_adapter":
        if not settings.internal_tool_http_base_url:
            raise ValueError(
                "ACQUIRING_AI_INTERNAL_TOOL_HTTP_BASE_URL is required when "
                "internal_tool_provider_backend=http_adapter"
            )
        return HttpInternalToolProvider(
            base_url=settings.internal_tool_http_base_url,
            timeout_seconds=settings.internal_tool_http_timeout_seconds,
            bearer_token=settings.internal_tool_http_bearer_token,
        )
    raise ValueError(
        "Unsupported internal tool provider backend: "
        f"{settings.internal_tool_provider_backend}"
    )


@lru_cache
def get_tool_execution_log_service() -> ToolExecutionLogService:
    return ToolExecutionLogService(
        session_factory=get_session_factory(),
        repository=ToolExecutionRepository(),
    )


@lru_cache
def get_observation_service() -> ObservationService:
    return ObservationService(
        session_factory=get_session_factory(),
        repository=ObservationRepository(),
    )


@lru_cache
def get_skill_registry() -> SkillRegistry:
    settings = get_settings()
    return SkillRegistry.from_directory(settings.skill_root)


@lru_cache
def get_workflow_registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@lru_cache
def get_workflow_service() -> WorkflowService:
    return WorkflowService(get_workflow_registry())
