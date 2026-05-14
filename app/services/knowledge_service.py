from __future__ import annotations

from typing import Dict, List

from app.schemas import BizDomain, KnowledgeHit


class KnowledgeService:
    """Small in-memory knowledge search service for the minimum usable MVP."""

    _knowledge_base: Dict[BizDomain, List[KnowledgeHit]] = {
        BizDomain.merchant: [
            KnowledgeHit(
                title="商户常见问题FAQ",
                snippet="面向商户常见业务问题的标准答复与处理指引。",
                source="K001",
            ),
            KnowledgeHit(
                title="商户入网规则手册",
                snippet="描述商户入网资料要求、审核口径和处理边界。",
                source="K002",
            ),
        ],
        BizDomain.operations: [
            KnowledgeHit(
                title="调额审核规则",
                snippet="包含调额阈值、风险标签和升级人工条件。",
                source="K004",
            ),
            KnowledgeHit(
                title="商户变更审核规范",
                snippet="包含商户变更材料要求和审批流程约束。",
                source="K003",
            ),
        ],
        BizDomain.data_support: [
            KnowledgeHit(
                title="销售数据指标字典",
                snippet="定义直营销售、区域和分公司的指标口径。",
                source="K008",
            ),
            KnowledgeHit(
                title="合规监管报表口径文档",
                snippet="说明固定监管报表字段和生成规则。",
                source="K007",
            ),
        ],
    }

    def search(self, biz_domain: BizDomain, query: str) -> List[KnowledgeHit]:
        hits = self._knowledge_base.get(biz_domain, [])
        if not query.strip():
            return hits
        lowered = query.lower()
        return [
            item
            for item in hits
            if lowered in item.title.lower() or lowered in item.snippet.lower()
        ] or hits
