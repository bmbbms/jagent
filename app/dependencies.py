from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.agents.router import RouterAgent
from app.config import get_settings
from app.db.init_db import init_db
from app.db.session import create_db_engine, create_session_factory
from app.registry.bootstrap import set_active_registrar
from app.registry.composite_registry import CompositeCapabilityRegistry
from app.registry.local_registry import LocalCapabilityRegistry
from app.registry.nacos_registry import NacosCapabilityRegistry
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.chat_repository import ChatRepository
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService
from app.services.skill_registry import SkillRegistry


@lru_cache
def get_engine():
    settings = get_settings()
    engine = create_db_engine(settings)
    if settings.database_auto_create:
        init_db(engine)
    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


@lru_cache
def get_capability_registry() -> CompositeCapabilityRegistry:
    settings = get_settings()
    local_registry = LocalCapabilityRegistry()
    secondary_registries = [
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

    import app.agents.capabilities  # noqa: F401

    return registry


@lru_cache
def get_router_agent() -> RouterAgent:
    return RouterAgent(capability_resolver=get_capability_registry())


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
def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService()


@lru_cache
def get_skill_registry() -> SkillRegistry:
    return SkillRegistry()
