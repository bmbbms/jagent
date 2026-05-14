from fastapi import APIRouter, Depends, Query

from app.dependencies import get_audit_service, get_knowledge_service
from app.schemas import BizDomain, KnowledgeSearchResponse
from app.services.audit_service import AuditService
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    biz_domain: BizDomain = Query(...),
    query: str = Query(default=""),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> KnowledgeSearchResponse:
    hits = knowledge_service.search(biz_domain=biz_domain, query=query)
    audit_service.record(
        action="knowledge.search",
        actor_id="system",
        payload={"biz_domain": biz_domain.value, "query": query, "hits": len(hits)},
    )
    return KnowledgeSearchResponse(query=query, biz_domain=biz_domain, hits=hits)
