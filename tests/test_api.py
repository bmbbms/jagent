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


def test_mcp_tools_api_and_overview(client: TestClient) -> None:
    tools_response = client.get("/api/mcp/tools")
    assert tools_response.status_code == 200
    tools = tools_response.json()
    assert isinstance(tools, list)
    assert tools
    first = tools[0]
    assert "tool_id" in first
    assert "provider" in first
    assert "transport" in first
    assert "call_count" in first

    filtered_response = client.get(
        "/api/mcp/tools",
        params={"provider": first["provider"], "transport": first["transport"]},
    )
    assert filtered_response.status_code == 200
    filtered = filtered_response.json()
    assert filtered
    assert all(item["provider"] == first["provider"] for item in filtered)
    assert all(item["transport"] == first["transport"] for item in filtered)

    overview_response = client.get("/api/mcp/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert "total" in overview
    assert "enabled_count" in overview
    assert "providers" in overview
    assert "transports" in overview

    recent_calls_response = client.get(
        f"/api/mcp/tools/{first['tool_id']}/recent-calls",
    )
    assert recent_calls_response.status_code == 200
    recent_calls = recent_calls_response.json()
    assert isinstance(recent_calls, list)


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

    filtered_response = client.get(
        "/api/capabilities",
        params={
            "risk_level": "high",
            "requires_approval": True,
            "transport": "inproc",
            "skill_id": "quota_review",
        },
    )
    assert filtered_response.status_code == 200
    filtered_body = filtered_response.json()
    assert filtered_body
    assert all(item["risk_level"] == "high" for item in filtered_body)
    assert all(item["requires_approval"] is True for item in filtered_body)
    assert all(item["transport"] == "inproc" for item in filtered_body)
    assert all("quota_review" in item["skills"] for item in filtered_body)

    health_filtered_response = client.get(
        "/api/capabilities",
        params={"source": "external", "health_status": "unknown"},
    )
    assert health_filtered_response.status_code == 200
    health_filtered_body = health_filtered_response.json()
    assert isinstance(health_filtered_body, list)
    if health_filtered_body:
        assert all("health_status" in item for item in health_filtered_body)


def test_capability_detail(client: TestClient) -> None:
    response = client.get("/api/capabilities/merchant.qa")
    assert response.status_code == 200
    body = response.json()
    assert body["capability_id"] == "merchant.qa"
    assert body["source"] == "local"
    assert "tags" in body
    assert "extras" in body
    assert "health_status" in body


def test_capability_overview(client: TestClient) -> None:
    response = client.get("/api/capabilities/overview/summary")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "local_count" in body
    assert "external_count" in body
    assert "domain_counts" in body
    assert "source_counts" in body
    assert "transport_counts" in body


def test_capability_recent_tasks_api(client: TestClient) -> None:
    response = client.get("/api/capabilities/merchant.qa/recent-tasks", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
      first = body[0]
      assert "task_id" in first
      assert "selected_agent_id" in first
      assert first["selected_agent_id"] == "merchant.qa"
      assert "status" in first
      assert "start_time" in first


def test_skills(client: TestClient) -> None:
    response = client.get("/api/skills", params={"biz_domain": "merchant"})
    assert response.status_code == 200
    body = response.json()
    skill_ids = {item["skill_id"] for item in body}
    assert "merchant_qa" in skill_ids
    assert "merchant_ops_analysis" in skill_ids

    filtered_response = client.get(
        "/api/skills",
        params={
            "allowed_tool": "merchant_profile_query",
            "has_human_escalation": True,
        },
    )
    assert filtered_response.status_code == 200
    filtered_body = filtered_response.json()
    assert filtered_body
    filtered_ids = {item["skill_id"] for item in filtered_body}
    assert "quota_review" in filtered_ids

    capability_filtered_response = client.get(
        "/api/skills",
        params={"capability_id": "operations.quota_review"},
    )
    assert capability_filtered_response.status_code == 200
    capability_filtered_body = capability_filtered_response.json()
    assert capability_filtered_body
    assert {item["skill_id"] for item in capability_filtered_body} == {"quota_review"}


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
            "risk_level": "high",
            "capability_id": "operations.quota_review",
            "workflow": "quota_review",
        },
    )
    assert list_response.status_code == 200
    approvals = list_response.json()
    assert any(item["approval_id"] == approval["approval_id"] for item in approvals)
    assert all(item["risk_level"] == "high" for item in approvals)
    assert all(item["capability_id"] == "operations.quota_review" for item in approvals)
    assert all(item["workflow"] == "quota_review" for item in approvals)

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

    governance_response = client.get(
        "/api/audit",
        params={
            "capability_id": "operations.quota_review",
            "workflow": "quota_review",
        },
    )
    assert governance_response.status_code == 200
    governance_body = governance_response.json()
    assert governance_body
    assert all(
        item["payload"].get("capability_id") == "operations.quota_review"
        for item in governance_body
    )
    assert all(item["payload"].get("workflow") == "quota_review" for item in governance_body)

    extended_response = client.get(
        "/api/audit",
        params={
            "source": "approval",
            "event_type": "approval",
            "outcome": 1,
        },
    )
    assert extended_response.status_code == 200
    extended_body = extended_response.json()
    assert extended_body
    assert all(item["source"] == "approval" for item in extended_body)
    assert all(item["event_type"] == "approval" for item in extended_body)
    assert all(item["outcome"] == 1 for item in extended_body)


def test_audit_overview_api(client: TestClient) -> None:
    response = client.get("/api/audit/overview")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "success_count" in body
    assert "failed_count" in body
    assert "pending_count" in body
    assert "source_counts" in body
    assert "event_type_counts" in body
    assert "action_counts" in body


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
    assert "output_overview" in body
    assert "observations" in body
    assert "runtime_sessions" in body
    assert "runtime_governance" in body
    assert "evaluation" in body
    assert isinstance(body["tool_calls"], list)
    assert isinstance(body["data_access_logs"], list)
    assert isinstance(body["structured_tool_results"], list)
    assert isinstance(body["output_overview"], dict)
    assert isinstance(body["observations"], list)
    assert isinstance(body["runtime_sessions"], list)
    assert isinstance(body["runtime_governance"], dict)
    assert body["structured_tool_results"]
    assert body["output_overview"]["total_deliverables"] >= 1
    assert body["output_overview"]["deliverables"]
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
    assert "runtime_session_count" in body["runtime_governance"]
    assert "fallback_count" in body["runtime_governance"]
    assert "mcp_call_count" in body["runtime_governance"]
    assert "mcp_error_count" in body["runtime_governance"]
    assert "mcp_providers" in body["runtime_governance"]
    assert "risk_flags" in body["runtime_governance"]
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


def test_task_output_overview_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-task-output-overview",
            "biz_domain": "operations",
            "message": "璇峰崗鍔╁仛璋冮瀹℃牳",
            "metadata": {"requested_agent_id": "operations.quota_review"},
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    overview_response = client.get(f"/api/tasks/{task_id}/output-overview")
    assert overview_response.status_code == 200
    body = overview_response.json()
    assert body["task_id"] == task_id
    assert body["total_deliverables"] >= 1
    assert isinstance(body["deliverables"], list)
    assert body["deliverables"]
    deliverable_types = {item["deliverable_type"] for item in body["deliverables"]}
    assert "final_response" in deliverable_types


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
            "risk_level": "low",
            "current_stage": "approval",
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
        assert item["risk_level"] == "low"
        assert item["current_stage"] == "approval"


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
    assert 'id="ticketCenterBtn"' in response.text
    assert 'id="approvalCenterBtn"' in response.text
    assert 'id="auditCenterBtn"' in response.text
    assert 'id="taskList"' in response.text
    assert 'id="outputOverview"' in response.text
    assert 'id="riskFilter"' in response.text
    assert 'id="stageFilter"' in response.text
    assert 'id="approvalFilterInput"' in response.text
    assert 'id="structuredToolResults"' in response.text
    assert 'id="workflowSnapshot"' in response.text
    assert 'id="skillSnapshot"' in response.text
    assert 'id="observations"' in response.text
    assert 'id="runtimeSessions"' in response.text
    assert 'id="runtimeGovernance"' in response.text
    assert "MCP 调用" in response.text
    assert "MCP Provider" in response.text
    assert 'id="pageSizeFilter"' in response.text
    assert 'id="sortByFilter"' in response.text
    assert 'id="prevPageBtn"' in response.text
    assert 'id="nextPageBtn"' in response.text
    assert 'data-open-suggestion=' in response.text or 'openEvaluationCenterBtn' in response.text
    assert 'data-open-ticket=' in response.text or 'ticketCenterBtn' in response.text


def test_external_agent_manager_ui_page(client: TestClient) -> None:
    response = client.get("/ui/external-agents?capability_id=external.stub.agent")
    assert response.status_code == 200
    assert '/ui/capabilities' in response.text
    assert '/ui/skills' in response.text
    assert 'id="listDomainFilter"' in response.text
    assert 'id="listSourceFilter"' in response.text
    assert 'id="listRiskFilter"' in response.text
    assert 'id="listApprovalFilter"' in response.text
    assert 'id="listTransportFilter"' in response.text
    assert 'id="listHealthFilter"' in response.text
    assert 'id="listCapabilityFilter"' in response.text
    assert 'id="healthOverview"' in response.text
    assert 'id="governanceOverview"' in response.text
    assert 'id="agentUrlInput"' in response.text
    assert 'id="capabilityNameInput"' in response.text
    assert 'id="discoverBtn"' in response.text
    assert 'id="addBtn"' in response.text
    assert 'id="updateBtn"' in response.text
    assert 'id="healthCheckBtn"' in response.text
    assert 'id="verifyBtn"' in response.text
    assert 'id="agentList"' in response.text
    assert 'id="recentTaskList"' in response.text


def test_external_agent_recent_tasks_api(client: TestClient) -> None:
    response = client.get("/api/external-agents/external.stub.agent/recent-tasks", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        first = body[0]
        assert "task_id" in first
        assert "selected_agent_id" in first
        assert first["selected_agent_id"] == "external.stub.agent"
        assert "status" in first
        assert "start_time" in first


def test_external_agent_list_supports_governance_filters(client: TestClient) -> None:
    response = client.get(
        "/api/external-agents",
        params={
            "risk_level": "low",
            "requires_approval": False,
            "transport": "http",
            "health_status": "unknown",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        assert all(item["risk_level"] == "low" for item in body)
        assert all(item["requires_approval"] is False for item in body)
        assert all(item["transport"] == "http" for item in body)
        assert all(item["health_status"] == "unknown" for item in body)


def test_external_agent_health_overview_api(client: TestClient) -> None:
    response = client.get("/api/external-agents/health-overview")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "healthy_count" in body
    assert "unhealthy_count" in body
    assert "unknown_count" in body


def test_external_agent_governance_overview_api(client: TestClient) -> None:
    response = client.get("/api/external-agents/governance-overview")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "approval_required_count" in body
    assert "high_risk_count" in body
    assert "source_counts" in body
    assert "transport_counts" in body
    assert "domain_counts" in body


def test_evaluations_ui_page(client: TestClient) -> None:
    response = client.get("/ui/evaluations")
    assert response.status_code == 200
    assert 'id="evaluationList"' in response.text
    assert 'id="evaluationDetail"' in response.text
    assert 'id="evaluationIdInput"' in response.text
    assert 'id="approvalPageBtn"' in response.text
    assert 'id="ticketPageBtn"' in response.text
    assert 'id="analyticsList"' in response.text
    assert 'id="agentFilterInput"' in response.text
    assert 'id="resultFilterInput"' in response.text
    assert 'id="suggestionList"' in response.text
    assert 'id="suggestionPriorityFilter"' in response.text
    assert 'id="loadSuggestionsBtn"' in response.text
    assert 'id="trendPanel"' in response.text
    assert 'id="focusAgentList"' in response.text
    assert "openAudit" in response.text or "/ui/audit?" in response.text
    assert response.text.count("function renderSuggestionOverview()") == 1
    assert response.text.count("function isSuggestionOverviewCardActive(item)") == 1
    assert response.text.count("async function loadSuggestions(") == 1


def test_evaluation_focus_agents_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-eval-focus",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200

    response = client.get("/api/evaluations/analytics/focus-agents", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    first = body[0]
    assert "agent_id" in first
    assert "attention_level" in first
    assert "suggestion_count" in first
    assert "backlog_suggestion_count" in first
    assert "high_priority_backlog_count" in first
    assert "ticket_bound_suggestion_count" in first
    assert "completed_ticket_count" in first
    assert "governance_score" in first
    assert "focus_reason" in first


def test_approvals_ui_page(client: TestClient) -> None:
    response = client.get("/ui/approvals")
    assert response.status_code == 200
    assert 'id="approvalList"' in response.text
    assert 'id="approvalDetail"' in response.text
    assert 'id="approvalIdInput"' in response.text
    assert 'id="statusFilter"' in response.text
    assert 'id="riskFilter"' in response.text
    assert 'id="requestedByFilter"' in response.text
    assert 'id="capabilityFilterInput"' in response.text
    assert 'id="workflowFilterInput"' in response.text
    assert 'id="workflowPageBtn"' in response.text
    assert 'id="capabilityPageBtn"' in response.text
    assert 'id="ticketPageBtn"' in response.text
    assert 'id="auditPageBtn"' in response.text
    assert 'id="openWorkflowBtn"' in response.text or "openWorkflowBtn" in response.text
    assert 'id="openCapabilityBtn"' in response.text or "openCapabilityBtn" in response.text


def test_service_tickets_ui_page(client: TestClient) -> None:
    response = client.get("/ui/service-tickets")
    assert response.status_code == 200
    assert 'id="ticketOverview"' in response.text
    assert 'id="ticketList"' in response.text
    assert 'id="ticketDetail"' in response.text
    assert 'id="ticketIdInput"' in response.text
    assert 'id="statusFilter"' in response.text
    assert 'id="sourceFilter"' in response.text
    assert 'id="priorityFilter"' in response.text
    assert 'id="ownerFilterInput"' in response.text
    assert 'id="requestedByFilterInput"' in response.text
    assert 'taskFilterInput' in response.text or 'task_id' in response.text
    assert 'id="evaluationPageBtn"' in response.text
    assert 'openTaskBtn' in response.text or '/ui/tasks?task_id=' in response.text
    assert 'openAuditBtn' in response.text or '/ui/audit?task_id=' in response.text


def test_service_ticket_overview_api(client: TestClient) -> None:
    response = client.get("/api/service-tickets/overview")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "submitted_count" in body
    assert "in_progress_count" in body
    assert "resolved_count" in body
    assert "closed_count" in body
    assert "backlog_count" in body
    assert "high_priority_count" in body
    assert "unassigned_count" in body
    assert "stale_open_count" in body
    assert "evaluation_source_count" in body
    assert "internal_tool_source_count" in body
    assert "completion_rate" in body


def test_audit_ui_page(client: TestClient) -> None:
    response = client.get("/ui/audit")
    assert response.status_code == 200
    assert 'id="auditOverview"' in response.text
    assert 'id="auditList"' in response.text
    assert 'id="auditDetail"' in response.text
    assert 'id="actionFilterInput"' in response.text
    assert 'id="actorFilterInput"' in response.text
    assert 'id="sourceFilterInput"' in response.text
    assert 'id="eventTypeFilterInput"' in response.text
    assert 'id="outcomeFilterInput"' in response.text
    assert 'id="capabilityFilterInput"' in response.text
    assert 'id="workflowFilterInput"' in response.text
    assert 'ticketFilterInput' in response.text or 'ticket_id' in response.text
    assert 'suggestionFilterInput' in response.text or 'suggestion_id' in response.text
    assert 'evaluationFilterInput' in response.text or 'evaluation_id' in response.text
    assert 'id="workflowPageBtn"' in response.text
    assert 'id="capabilityPageBtn"' in response.text
    assert 'id="openApprovalBtn"' in response.text or "openApprovalBtn" in response.text
    assert 'id="openCapabilityBtn"' in response.text or "openCapabilityBtn" in response.text
    assert 'openTicketBtn' in response.text or '/ui/service-tickets?ticket_id=' in response.text
    assert 'openSuggestionBtn' in response.text or 'suggestion_id=' in response.text


def test_workflows_ui_page(client: TestClient) -> None:
    response = client.get("/ui/workflows")
    assert response.status_code == 200
    assert 'id="workflowList"' in response.text
    assert 'id="workflowDetail"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="requiredToolInput"' in response.text
    assert 'id="approvalFilter"' in response.text
    assert 'id="auditTagInput"' in response.text
    assert 'id="fallbackRuleInput"' in response.text
    assert 'id="workflowCodeInput"' in response.text
    assert 'id="loadBtn"' in response.text


def test_skills_ui_page(client: TestClient) -> None:
    response = client.get("/ui/skills")
    assert response.status_code == 200
    assert 'id="skillList"' in response.text
    assert 'id="skillDetail"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="toolFilterInput"' in response.text
    assert 'id="escalationFilter"' in response.text
    assert 'id="capabilityPageBtn"' in response.text
    assert 'id="capabilityFilterInput"' in response.text
    assert 'id="skillIdInput"' in response.text
    assert 'id="loadBtn"' in response.text


def test_capabilities_ui_page(client: TestClient) -> None:
    response = client.get("/ui/capabilities")
    assert response.status_code == 200
    assert 'id="capabilityOverview"' in response.text
    assert 'id="capabilityList"' in response.text
    assert 'id="capabilityDetail"' in response.text
    assert 'id="capabilityRecentTaskList"' in response.text
    assert 'id="domainFilter"' in response.text
    assert 'id="sourceFilter"' in response.text
    assert 'id="riskFilter"' in response.text
    assert 'id="approvalFilter"' in response.text
    assert 'id="transportFilter"' in response.text
    assert 'id="healthFilter"' in response.text
    assert 'id="skillFilterInput"' in response.text
    assert 'id="capabilityIdInput"' in response.text


def test_mcp_ui_page(client: TestClient) -> None:
    response = client.get("/ui/mcp")
    assert response.status_code == 200
    assert 'id="providerFilter"' in response.text
    assert 'id="transportFilter"' in response.text
    assert 'id="enabledFilter"' in response.text
    assert 'id="calledFilter"' in response.text
    assert 'id="loadBtn"' in response.text
    assert 'id="overview"' in response.text
    assert 'id="toolList"' in response.text
    assert 'id="toolDetail"' in response.text
    assert 'id="recentCalls"' in response.text
    assert "/api/mcp/tools" in response.text


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


def test_evaluation_analytics_trend_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-eval-trend",
            "biz_domain": "merchant",
            "message": "请帮我解答商户规则问题",
        },
    )
    assert chat_response.status_code == 200
    agent_id = chat_response.json()["capability_id"]

    response = client.get(
        "/api/evaluations/analytics/trend",
        params={"agent_id": agent_id, "limit": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == agent_id
    assert "evaluation_count" in body
    assert "latest_overall_score" in body
    assert "score_delta" in body
    assert "improving" in body
    assert "points" in body
    assert isinstance(body["points"], list)
    assert body["points"]
    assert body["points"][-1]["agent_id"] == agent_id


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
    chat_body = chat_response.json()
    agent_id = chat_body["capability_id"]
    task_id = chat_body["task_id"]

    list_response = client.get("/api/evaluations/suggestions", params={"agent_id": agent_id})
    assert list_response.status_code == 200
    suggestions = list_response.json()
    assert isinstance(suggestions, list)
    assert suggestions
    first = suggestions[0]
    assert "suggestion_id" in first
    assert "status" in first
    assert "priority" in first
    assert "source_type" in first
    assert "source_ref" in first

    overview_response = client.get(
        "/api/evaluations/suggestions/overview",
        params={"agent_id": agent_id},
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert "total" in overview
    assert overview["total"] >= 1
    assert "ticket_bound_count" in overview
    assert "ticket_unbound_count" in overview
    assert "completed_ticket_count" in overview
    assert "backlog_count" in overview
    assert "high_priority_backlog_count" in overview
    assert "completion_rate" in overview

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

    ticket_response = client.post(
        f"/api/evaluations/suggestions/{first['suggestion_id']}/ticket",
        json={
            "requested_by": "agent-ops",
            "owner": "agent-ops",
            "priority": "high",
            "comment": "转为评估优化工单",
        },
    )
    assert ticket_response.status_code == 200
    ticket_bound = ticket_response.json()
    assert ticket_bound["ticket_id"] is not None
    assert ticket_bound["ticket_status"] == "submitted"
    assert ticket_bound["status"] == "in_progress"

    priority_filtered_response = client.get(
        "/api/evaluations/suggestions",
        params={"agent_id": agent_id, "priority": "high"},
    )
    assert priority_filtered_response.status_code == 200
    priority_filtered = priority_filtered_response.json()
    assert priority_filtered
    assert all(item["priority"] == "high" for item in priority_filtered)

    status_overview_response = client.get(
        "/api/evaluations/suggestions/overview",
        params={
            "agent_id": agent_id,
            "status": "in_progress",
            "priority": "high",
            "owner": "agent-ops",
        },
    )
    assert status_overview_response.status_code == 200
    status_overview = status_overview_response.json()
    assert status_overview["total"] >= 1
    assert status_overview["in_progress_count"] == status_overview["total"]
    assert status_overview["ticket_bound_count"] >= 1

    ticket_list_response = client.get(
        "/api/service-tickets",
        params={"source": "evaluation", "requested_by": "agent-ops"},
    )
    assert ticket_list_response.status_code == 200
    tickets = ticket_list_response.json()
    assert tickets
    ticket = next(item for item in tickets if item["ticket_id"] == ticket_bound["ticket_id"])
    assert ticket["linked_suggestion_id"] == first["suggestion_id"]
    assert ticket["linked_evaluation_id"] is not None
    assert ticket["owner"] == "agent-ops"
    assert ticket["linked_task_id"] == task_id

    task_filtered_ticket_list_response = client.get(
        "/api/service-tickets",
        params={"task_id": task_id},
    )
    assert task_filtered_ticket_list_response.status_code == 200
    task_filtered_tickets = task_filtered_ticket_list_response.json()
    assert any(item["ticket_id"] == ticket_bound["ticket_id"] for item in task_filtered_tickets)

    ticket_detail_response = client.get(f"/api/service-tickets/{ticket_bound['ticket_id']}")
    assert ticket_detail_response.status_code == 200
    ticket_detail = ticket_detail_response.json()
    assert ticket_detail["ticket_id"] == ticket_bound["ticket_id"]
    assert ticket_detail["source"] == "evaluation"
    assert ticket_detail["linked_task_id"] == task_id

    ticket_update_response = client.put(
        f"/api/service-tickets/{ticket_bound['ticket_id']}",
        json={
            "status": "resolved",
            "owner": "agent-optimizer",
            "priority": "medium",
        },
    )
    assert ticket_update_response.status_code == 200
    updated_ticket = ticket_update_response.json()
    assert updated_ticket["status"] == "resolved"
    assert updated_ticket["owner"] == "agent-optimizer"
    assert updated_ticket["priority"] == "medium"
    assert updated_ticket["closed_at"] is not None

    synced_suggestion_response = client.get(
        "/api/evaluations/suggestions",
        params={"agent_id": agent_id, "owner": "agent-optimizer"},
    )
    assert synced_suggestion_response.status_code == 200
    synced_suggestions = synced_suggestion_response.json()
    synced = next(item for item in synced_suggestions if item["suggestion_id"] == first["suggestion_id"])
    assert synced["ticket_id"] == ticket_bound["ticket_id"]
    assert synced["ticket_status"] == "resolved"
    assert synced["status"] == "completed"
    assert synced["priority"] == "medium"
    assert synced["owner"] == "agent-optimizer"
    assert synced["closed_at"] is not None

    ticket_audit_response = client.get(
        "/api/audit",
        params={"task_id": task_id},
    )
    assert ticket_audit_response.status_code == 200
    ticket_audit_events = ticket_audit_response.json()
    audit_actions = {item["action"] for item in ticket_audit_events}
    assert "service_ticket.create" in audit_actions
    assert "service_ticket.update" in audit_actions

    ticket_id_audit_response = client.get(
        "/api/audit",
        params={"ticket_id": ticket_bound["ticket_id"]},
    )
    assert ticket_id_audit_response.status_code == 200
    ticket_id_audit_events = ticket_id_audit_response.json()
    assert ticket_id_audit_events
    assert all(item["payload"].get("ticket_id") == ticket_bound["ticket_id"] for item in ticket_id_audit_events)

    suggestion_id_audit_response = client.get(
        "/api/audit",
        params={"suggestion_id": first["suggestion_id"]},
    )
    assert suggestion_id_audit_response.status_code == 200
    suggestion_id_audit_events = suggestion_id_audit_response.json()
    assert suggestion_id_audit_events
    assert all(item["payload"].get("suggestion_id") == first["suggestion_id"] for item in suggestion_id_audit_events)

    evaluation_id_audit_response = client.get(
        "/api/audit",
        params={"evaluation_id": ticket["linked_evaluation_id"]},
    )
    assert evaluation_id_audit_response.status_code == 200
    evaluation_id_audit_events = evaluation_id_audit_response.json()
    assert evaluation_id_audit_events
    assert all(item["payload"].get("evaluation_id") == ticket["linked_evaluation_id"] for item in evaluation_id_audit_events)

    final_overview_response = client.get(
        "/api/evaluations/suggestions/overview",
        params={"agent_id": agent_id},
    )
    assert final_overview_response.status_code == 200
    final_overview = final_overview_response.json()
    assert final_overview["ticket_bound_count"] >= 1
    assert final_overview["completed_ticket_count"] >= 1
    assert final_overview["completion_rate"] >= 0


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

    governance_filtered_response = client.get(
        "/api/workflows",
        params={
            "required_tool": "quota_approval_submit",
            "has_approval_points": True,
            "audit_tag": "approval",
            "fallback_rule": "转人工",
        },
    )
    assert governance_filtered_response.status_code == 200
    governance_items = governance_filtered_response.json()
    assert governance_items
    assert all("quota_approval_submit" in item["required_tools"] for item in governance_items)
    assert all(item["approval_points"] for item in governance_items)
    assert all("approval" in item["audit_tags"] for item in governance_items)
    assert all(any("转人工" in rule for rule in item["fallback_rules"]) for item in governance_items)

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
