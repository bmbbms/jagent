from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_home(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "Acquiring AI"
    assert body["capabilities"]


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capabilities(client: TestClient) -> None:
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    body = response.json()
    merchant_qa = next(item for item in body if item["capability_id"] == "merchant.qa")
    assert "merchant_qa" in merchant_qa["skills"]


def test_skills(client: TestClient) -> None:
    response = client.get("/api/skills", params={"biz_domain": "merchant"})
    assert response.status_code == 200
    body = response.json()
    skill_ids = {item["skill_id"] for item in body}
    assert "merchant_qa" in skill_ids
    assert "merchant_ops_analysis" in skill_ids


def test_chat_merchant(client: TestClient) -> None:
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
    assert "Runtime=agentscope" in body["routing_trace"]["reason"]


def test_chat_operations_creates_approval(client: TestClient) -> None:
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


def test_knowledge_search(client: TestClient) -> None:
    response = client.get(
        "/api/knowledge/search",
        params={"biz_domain": "operations", "query": "调额"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["biz_domain"] == "operations"
    assert body["hits"]


def test_create_and_decide_approval(client: TestClient) -> None:
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


def test_audit_events(client: TestClient) -> None:
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_task_detail_includes_tool_execution_details(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-task-detail",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    detail_response = client.get(f"/api/tasks/{task_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert "tool_calls" in body
    assert "data_access_logs" in body
    assert "structured_tool_results" in body
    assert "observations" in body
    assert "runtime_sessions" in body
    assert "evaluation" in body
    assert isinstance(body["tool_calls"], list)
    assert isinstance(body["data_access_logs"], list)
    assert isinstance(body["structured_tool_results"], list)
    assert isinstance(body["observations"], list)
    assert isinstance(body["runtime_sessions"], list)
    assert body["structured_tool_results"]
    assert body["observations"]
    assert body["runtime_sessions"]
    first_tool_result = body["structured_tool_results"][0]
    assert "tool_id" in first_tool_result
    assert "result" in first_tool_result
    phases = {item["phase"] for item in body["observations"]}
    assert {"planner", "bridge", "executor"}.issubset(phases)
    assert body["runtime_sessions"][0]["observation_count"] >= 1
    assert body["evaluation"] is not None


def test_task_tool_call_and_data_access_apis(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-task-log-api",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    tool_call_response = client.get(f"/api/tasks/{task_id}/tool-calls")
    assert tool_call_response.status_code == 200
    tool_calls = tool_call_response.json()
    assert isinstance(tool_calls, list)

    data_access_response = client.get(f"/api/tasks/{task_id}/data-access")
    assert data_access_response.status_code == 200
    data_access_logs = data_access_response.json()
    assert isinstance(data_access_logs, list)

    observation_response = client.get(f"/api/tasks/{task_id}/observations")
    assert observation_response.status_code == 200
    observations = observation_response.json()
    assert isinstance(observations, list)
    assert observations
    assert observations[0]["task_id"] == task_id

    runtime_session_response = client.get(f"/api/tasks/{task_id}/runtime-sessions")
    assert runtime_session_response.status_code == 200
    runtime_sessions = runtime_session_response.json()
    assert isinstance(runtime_sessions, list)
    assert runtime_sessions
    assert runtime_sessions[0]["session_id"]


def test_task_evaluation_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-task-evaluation",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    evaluation_response = client.get(f"/api/tasks/{task_id}/evaluation")
    assert evaluation_response.status_code == 200
    body = evaluation_response.json()
    assert body["task_id"] == task_id
    assert "overall_score" in body
    assert isinstance(body["details"], list)
    assert any(item["dimension_code"] == "efficiency" for item in body["details"])
    assert "fallback" in body["summary"] or "工具调用" in body["summary"] or "次工具调用" in body["summary"]
    assert isinstance(body["suggestions"], list)
    assert any(item["optimization_type"] in {"runtime", "workflow", "tool", "prompt"} for item in body["suggestions"])


def test_task_list_supports_filters(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        params={
            "status": "waiting_approval",
            "biz_domain": "operations",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["page_size"] == 50
    for item in body["items"]:
        assert item["status"] == "waiting_approval"
        assert item["biz_domain"] == "operations"


def test_task_list_supports_extended_filters(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        params={
            "status": "waiting_approval",
            "biz_domain": "operations",
            "selected_agent_id": "operations.quota_review",
            "start_date_from": "2026-01-01",
            "start_date_to": "2026-12-31",
            "page_size": 20,
            "page": 1,
            "sort_by": "start_time",
            "sort_order": "desc",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["sort_by"] == "start_time"
    assert body["sort_order"] == "desc"
    assert len(body["items"]) <= 20
    for item in body["items"]:
        assert item["status"] == "waiting_approval"
        assert item["biz_domain"] == "operations"
        assert item["selected_agent_id"] == "operations.quota_review"


def test_task_list_supports_pagination_and_legacy_limit(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        params={
            "page": 1,
            "limit": 10,
            "sort_by": "start_time",
            "sort_order": "desc",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["sort_by"] == "start_time"
    assert body["sort_order"] == "desc"
    assert len(body["items"]) <= 10
    assert body["total"] >= len(body["items"])


def test_task_realtime_ui_page(client: TestClient) -> None:
    response = client.get("/ui/tasks")
    assert response.status_code == 200
    assert 'id="agentManagerBtn"' in response.text
    assert 'id="taskList"' in response.text
    assert 'id="structuredToolResults"' in response.text
    assert 'id="observations"' in response.text
    assert 'id="runtimeSessions"' in response.text
    assert 'id="pageSizeFilter"' in response.text
    assert 'id="sortByFilter"' in response.text
    assert 'id="prevPageBtn"' in response.text
    assert 'id="nextPageBtn"' in response.text


def test_external_agent_manager_ui_page(client: TestClient) -> None:
    response = client.get("/ui/external-agents")
    assert response.status_code == 200
    assert 'id="agentUrlInput"' in response.text
    assert 'id="discoverBtn"' in response.text
    assert 'id="addBtn"' in response.text
    assert 'id="verifyBtn"' in response.text
    assert 'id="agentList"' in response.text


def test_evaluations_ui_page(client: TestClient) -> None:
    response = client.get("/ui/evaluations")
    assert response.status_code == 200
    assert 'id="evaluationList"' in response.text
    assert 'id="evaluationDetail"' in response.text
    assert 'id="evaluationIdInput"' in response.text
    assert 'id="analyticsList"' in response.text
    assert 'id="agentFilterInput"' in response.text
    assert 'id="resultFilterInput"' in response.text


def test_evaluation_analytics_api(client: TestClient) -> None:
    client.post(
        "/api/chat",
        json={
            "user_id": "u-eval-analytics",
            "biz_domain": "merchant",
            "message": "请帮我解答商户规则问题",
        },
    )
    response = client.get("/api/evaluations/analytics/by-agent")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    assert "agent_id" in body[0]
    assert "average_overall_score" in body[0]


def test_workflow_api_and_task_workflow_events(client: TestClient) -> None:
    list_response = client.get("/api/workflows", params={"biz_domain": "operations"})
    assert list_response.status_code == 200
    workflow_items = list_response.json()
    assert workflow_items
    workflow_codes = {item["workflow_code"] for item in workflow_items}
    assert "quota_review" in workflow_codes

    detail_response = client.get("/api/workflows/quota_review")
    assert detail_response.status_code == 200
    workflow_detail = detail_response.json()
    assert workflow_detail["workflow_code"] == "quota_review"
    assert workflow_detail["steps"]

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-workflow",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    task_detail_response = client.get(f"/api/tasks/{task_id}")
    assert task_detail_response.status_code == 200
    task_detail = task_detail_response.json()
    event_types = [item["event_type"] for item in task_detail["events"]]
    assert "workflow_started" in event_types
    assert "workflow_step_registered" in event_types
    assert "workflow_approval_checkpoint" in event_types
