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
    assert "/api/skills" in body["endpoints"]


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
    assert merchant_qa["source"] == "local"
    assert "risk_level" in merchant_qa
    assert "requires_approval" in merchant_qa
    assert "transport" in merchant_qa


def test_capabilities_support_source_filter(client: TestClient) -> None:
    response = client.get("/api/capabilities", params={"source": "local"})
    assert response.status_code == 200
    body = response.json()
    assert body
    assert all(item["source"] == "local" for item in body)

    external_response = client.get("/api/capabilities", params={"source": "external"})
    assert external_response.status_code == 200
    assert isinstance(external_response.json(), list)


def test_capability_detail(client: TestClient) -> None:
    response = client.get("/api/capabilities/merchant.qa")
    assert response.status_code == 200
    body = response.json()
    assert body["capability_id"] == "merchant.qa"
    assert body["source"] == "local"
    assert "tags" in body
    assert "extras" in body


def test_skills(client: TestClient) -> None:
    response = client.get("/api/skills", params={"biz_domain": "merchant"})
    assert response.status_code == 200
    body = response.json()
    skill_ids = {item["skill_id"] for item in body}
    assert "merchant_qa" in skill_ids
    assert "merchant_ops_analysis" in skill_ids


def test_skill_detail(client: TestClient) -> None:
    response = client.get("/api/skills/merchant_qa")
    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == "merchant_qa"
    assert isinstance(body["required_inputs"], list)
    assert isinstance(body["steps"], list)
    assert isinstance(body["allowed_tools"], list)


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


def test_approval_list_filters_and_detail_api(client: TestClient) -> None:
    create_response = client.post(
        "/api/approvals",
        json={
            "title": "过滤审批测试",
            "biz_domain": "operations",
            "requested_by": "u-approval-filter",
            "risk_level": "high",
            "capability_id": "operations.quota_review",
            "workflow": "quota_review",
            "payload": {"task_id": "task-approval-filter"},
        },
    )
    assert create_response.status_code == 200
    approval = create_response.json()

    list_response = client.get(
        "/api/approvals",
        params={
            "status": "pending",
            "biz_domain": "operations",
            "requested_by": "u-approval-filter",
        },
    )
    assert list_response.status_code == 200
    approvals = list_response.json()
    assert any(item["approval_id"] == approval["approval_id"] for item in approvals)

    detail_response = client.get(f"/api/approvals/{approval['approval_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["approval_id"] == approval["approval_id"]
    assert detail["task_id"] == "task-approval-filter"
    assert detail["status"] == "pending"


def test_audit_events(client: TestClient) -> None:
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_audit_events_support_filters(client: TestClient) -> None:
    client.post(
        "/api/approvals",
        json={
            "title": "审计过滤测试",
            "biz_domain": "operations",
            "requested_by": "u-audit-filter",
            "risk_level": "high",
            "capability_id": "operations.quota_review",
            "workflow": "quota_review",
            "payload": {"task_id": "task-audit-filter"},
        },
    )
    response = client.get(
        "/api/audit",
        params={
            "action": "approval.create",
            "actor_id": "u-audit-filter",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(item["action"] == "approval.create" for item in body)
    assert all(item["actor_id"] == "u-audit-filter" for item in body)


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
    assert "runtime_session_id" in first_tool_result
    phases = {item["phase"] for item in body["observations"]}
    assert {"planner", "bridge", "executor"}.issubset(phases)
    assert body["runtime_sessions"][0]["observation_count"] >= 1
    assert body["runtime_sessions"][0]["tool_call_count"] >= 1
    assert body["evaluation"] is not None
    event_titles = {item["title"] for item in body["events"]}
    assert "任务已创建" in event_titles
    assert "生成最终回复" in event_titles
    tool_runtime_session_ids = {
        item["runtime_session_id"] for item in body["tool_calls"] if item.get("runtime_session_id")
    }
    observation_session_ids = {
        item["session_id"] for item in body["observations"] if item.get("session_id")
    }
    assert tool_runtime_session_ids
    assert tool_runtime_session_ids.issubset(observation_session_ids)
    data_access_runtime_session_ids = {
        item["runtime_session_id"]
        for item in body["data_access_logs"]
        if item.get("runtime_session_id")
    }
    assert data_access_runtime_session_ids.issubset(tool_runtime_session_ids)


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
    assert tool_calls
    assert any(item.get("runtime_session_id") for item in tool_calls)

    data_access_response = client.get(f"/api/tasks/{task_id}/data-access")
    assert data_access_response.status_code == 200
    data_access_logs = data_access_response.json()
    assert isinstance(data_access_logs, list)
    assert data_access_logs
    assert all("runtime_session_id" in item for item in data_access_logs)

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
    assert 'id="capabilityCenterBtn"' in response.text
    assert 'id="workflowCenterBtn"' in response.text
    assert 'id="skillCenterBtn"' in response.text
    assert 'id="evaluationCenterBtn"' in response.text
    assert 'id="approvalCenterBtn"' in response.text
    assert 'id="auditCenterBtn"' in response.text
    assert 'id="taskList"' in response.text
    assert 'id="structuredToolResults"' in response.text
    assert 'id="workflowSnapshot"' in response.text
    assert 'id="skillSnapshot"' in response.text
    assert 'id="observations"' in response.text
    assert 'id="runtimeSessions"' in response.text
    assert 'id="pageSizeFilter"' in response.text
    assert 'id="sortByFilter"' in response.text
    assert 'id="prevPageBtn"' in response.text
    assert 'id="nextPageBtn"' in response.text
    assert 'data-open-suggestion=' in response.text or 'openEvaluationCenterBtn' in response.text


def test_external_agent_manager_ui_page(client: TestClient) -> None:
    response = client.get("/ui/external-agents?capability_id=external.stub.agent")
    assert response.status_code == 200
    assert '/ui/capabilities' in response.text
    assert '/ui/skills' in response.text
    assert 'id="listDomainFilter"' in response.text
    assert 'id="listSourceFilter"' in response.text
    assert 'id="listCapabilityFilter"' in response.text
    assert 'id="agentUrlInput"' in response.text
    assert 'id="capabilityNameInput"' in response.text
    assert 'id="discoverBtn"' in response.text
    assert 'id="addBtn"' in response.text
    assert 'id="updateBtn"' in response.text
    assert 'id="verifyBtn"' in response.text
    assert 'id="agentList"' in response.text


def test_evaluations_ui_page(client: TestClient) -> None:
    response = client.get("/ui/evaluations")
    assert response.status_code == 200
    assert 'id="evaluationList"' in response.text
    assert 'id="evaluationDetail"' in response.text
    assert 'id="evaluationIdInput"' in response.text
    assert 'id="approvalPageBtn"' in response.text
    assert 'id="analyticsList"' in response.text
    assert 'id="agentFilterInput"' in response.text
    assert 'id="resultFilterInput"' in response.text
    assert 'id="suggestionList"' in response.text
    assert 'id="loadSuggestionsBtn"' in response.text


def test_approvals_ui_page(client: TestClient) -> None:
    response = client.get("/ui/approvals")
    assert response.status_code == 200
    assert 'id="approvalList"' in response.text
    assert 'id="approvalDetail"' in response.text
    assert 'id="approvalIdInput"' in response.text
    assert 'id="statusFilter"' in response.text
    assert 'id="requestedByFilter"' in response.text
    assert 'id="workflowPageBtn"' in response.text
    assert 'id="capabilityPageBtn"' in response.text
    assert 'id="auditPageBtn"' in response.text
    assert 'id="openWorkflowBtn"' in response.text or "openWorkflowBtn" in response.text
    assert 'id="openCapabilityBtn"' in response.text or "openCapabilityBtn" in response.text


def test_audit_ui_page(client: TestClient) -> None:
    response = client.get("/ui/audit")
    assert response.status_code == 200
    assert 'id="auditList"' in response.text
    assert 'id="auditDetail"' in response.text
    assert 'id="actionFilterInput"' in response.text
    assert 'id="actorFilterInput"' in response.text


def test_workflows_ui_page(client: TestClient) -> None:
    response = client.get("/ui/workflows")
    assert response.status_code == 200
    assert 'id="workflowList"' in response.text
    assert 'id="workflowDetail"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="workflowCodeInput"' in response.text
    assert 'id="loadBtn"' in response.text


def test_skills_ui_page(client: TestClient) -> None:
    response = client.get("/ui/skills")
    assert response.status_code == 200
    assert 'id="skillList"' in response.text
    assert 'id="skillDetail"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="skillIdInput"' in response.text
    assert 'id="loadBtn"' in response.text


def test_capabilities_ui_page(client: TestClient) -> None:
    response = client.get("/ui/capabilities")
    assert response.status_code == 200
    assert 'id="capabilityList"' in response.text
    assert 'id="capabilityDetail"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="sourceFilter"' in response.text
    assert 'id="capabilityIdInput"' in response.text


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
    assert "poor_rate" in body[0]
    assert "fallback_related_count" in body[0]
    assert "attention_level" in body[0]


def test_evaluation_analytics_overview_api(client: TestClient) -> None:
    response = client.get("/api/evaluations/analytics/overview")
    assert response.status_code == 200
    body = response.json()
    assert "evaluation_count" in body
    assert "agent_count" in body
    assert "poor_evaluation_count" in body
    assert "high_attention_agent_count" in body
    assert "average_overall_score" in body


def test_evaluation_list_supports_extended_filters(client: TestClient) -> None:
    response = client.get(
        "/api/evaluations",
        params={
            "start_date_from": "2026-01-01",
            "start_date_to": "2026-12-31",
            "min_overall_score": 70,
            "attention_level": "normal",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert item["overall_score"] >= 70


def test_evaluation_suggestion_apis(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-eval-suggestion",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    agent_id = chat_response.json()["capability_id"]

    list_response = client.get("/api/evaluations/suggestions", params={"agent_id": agent_id})
    assert list_response.status_code == 200
    suggestions = list_response.json()
    assert isinstance(suggestions, list)
    assert suggestions
    first = suggestions[0]
    assert "suggestion_id" in first
    assert "status" in first
    assert "priority" in first

    overview_response = client.get(
        "/api/evaluations/suggestions/overview",
        params={"agent_id": agent_id},
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert "total" in overview
    assert overview["total"] >= 1

    update_response = client.put(
        f"/api/evaluations/suggestions/{first['suggestion_id']}",
        json={
            "status": "in_progress",
            "owner": "agent-ops",
            "priority": "high",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "in_progress"
    assert updated["owner"] == "agent-ops"
    assert updated["priority"] == "high"


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

    filtered_response = client.get("/api/workflows", params={"workflow_code": "quota_review"})
    assert filtered_response.status_code == 200
    filtered_items = filtered_response.json()
    assert len(filtered_items) == 1
    assert filtered_items[0]["workflow_code"] == "quota_review"

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
