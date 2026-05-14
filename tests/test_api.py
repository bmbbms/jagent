from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "Acquiring AI"
    assert body["capabilities"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capabilities() -> None:
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    body = response.json()
    merchant_qa = next(item for item in body if item["capability_id"] == "merchant.qa")
    assert "merchant_qa" in merchant_qa["skills"]


def test_skills() -> None:
    response = client.get("/api/skills", params={"biz_domain": "merchant"})
    assert response.status_code == 200
    body = response.json()
    skill_ids = {item["skill_id"] for item in body}
    assert "merchant_qa" in skill_ids
    assert "merchant_ops_analysis" in skill_ids


def test_chat_merchant() -> None:
    response = client.post(
        "/api/chat",
        json={
            "user_id": "u-001",
            "biz_domain": "merchant",
            "message": "请帮我解答商户规则问题",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "merchant"
    assert body["capability_id"] == "merchant.qa"
    assert body["approval_id"] is None
    assert body["routing_trace"]["selected_capability_id"] == "merchant.qa"
    assert "merchant.qa" in body["routing_trace"]["matched_capability_ids"]
    assert "merchant_qa" in body["routing_trace"]["declared_skills"]
    assert "Runtime=agno" in body["routing_trace"]["reason"]


def test_chat_operations_creates_approval() -> None:
    response = client.post(
        "/api/chat",
        json={
            "user_id": "u-002",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capability_id"] == "operations.quota_review"
    assert body["requires_approval"] is True
    assert body["approval_id"] is not None
    assert body["routing_trace"]["selected_capability_id"] == "operations.quota_review"


def test_knowledge_search() -> None:
    response = client.get(
        "/api/knowledge/search",
        params={"biz_domain": "operations", "query": "调额"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["biz_domain"] == "operations"
    assert body["hits"]


def test_create_and_decide_approval() -> None:
    create_response = client.post(
        "/api/approvals",
        json={
            "title": "手工创建审批",
            "biz_domain": "operations",
            "requested_by": "u-003",
            "risk_level": "high",
            "capability_id": "operations.quota_review",
            "workflow": "quota_review",
            "payload": {"demo": True},
        },
    )
    assert create_response.status_code == 200
    approval_id = create_response.json()["approval_id"]

    decide_response = client.post(
        f"/api/approvals/{approval_id}/decision",
        json={
            "reviewer_id": "reviewer-1",
            "decision": "approve",
            "comment": "通过",
        },
    )
    assert decide_response.status_code == 200
    assert decide_response.json()["status"] == "approved"


def test_audit_events() -> None:
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
