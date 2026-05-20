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
    assert "disabled_tool_count" in overview
    assert "slow_tool_count" in overview
    assert "total_failure_count" in overview
    assert "high_risk_tool_count" in overview
    assert "providers" in overview
    assert "transports" in overview
    assert "provider_failure_counts" in overview
    assert "transport_failure_counts" in overview

    governance_issue_response = client.get("/api/mcp/governance-issues")
    assert governance_issue_response.status_code == 200
    governance_issues = governance_issue_response.json()
    assert isinstance(governance_issues, list)
    if governance_issues:
        first_issue = governance_issues[0]
        assert "tool_id" in first_issue
        assert "governance_status" in first_issue
        assert "reasons" in first_issue
        assert "recommended_action" in first_issue

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


def test_agent_profile_recent_tasks_api(client: TestClient) -> None:
    response = client.get("/api/agent-profiles/merchant.qa/recent-tasks", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        first = body[0]
        assert "task_id" in first
        assert "selected_agent_id" in first
        assert first["selected_agent_id"] == "merchant.qa"
        assert "gateway_reason" in first


def test_agent_profile_evaluation_summary_api(client: TestClient) -> None:
    response = client.get("/api/agent-profiles/merchant.qa/evaluation-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "merchant.qa"
    assert "evaluation_count" in body
    assert "attention_level" in body
    assert "average_overall_score" in body
    assert "focus_reason" in body
    assert "latest_result_label" in body


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
    assert body["routing_trace"]["selected_capability_id"] == "merchant.qa"
    assert "merchant.qa" in body["routing_trace"]["matched_capability_ids"]
    assert "merchant_qa" in body["routing_trace"]["declared_skills"]
    assert "Runtime=agentscope" in body["routing_trace"]["reason"]


def test_chat_operations_disables_approval_flow(client: TestClient) -> None:
    response = client.post(
        "/api/chat",
        json={
            "user_id": "u-002",
            "biz_domain": "operations",
            "message": "quota review",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capability_id"] == "operations.quota_review"
    assert body["requires_approval"] is False
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

    audit_response = client.get(
        "/api/audit",
        params={"action": "knowledge.search", "actor_id": "system"},
    )
    assert audit_response.status_code == 200
    audit_items = audit_response.json()
    assert audit_items
    latest = audit_items[0]
    assert latest["source"] == "knowledge"
    assert latest["event_type"] == "knowledge_search"
    assert latest["outcome"] == 1
    assert latest["payload"]["request_summary"] == body["query"]
    assert latest["payload"]["response_summary"].startswith("knowledge hits=")
    assert latest["payload"]["payload"]["biz_domain"] == "operations"
    assert latest["payload"]["payload"]["query"] == body["query"]
    assert latest["payload"]["payload"]["hits"] >= 1
    assert latest["payload"]["payload"]["hit_sources"]


def test_audit_events(client: TestClient) -> None:
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_audit_events_support_filters(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-audit-filter",
            "biz_domain": "operations",
            "message": "quota review",
        },
    )
    assert chat_response.status_code == 200

    response = client.get(
        "/api/audit",
        params={
            "action": "chat.request",
            "actor_id": "u-audit-filter",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(item["action"] == "chat.request" for item in body)
    assert all(item["actor_id"] == "u-audit-filter" for item in body)
    latest_chat_audit = body[0]
    assert latest_chat_audit["source"] == "chat"
    assert latest_chat_audit["event_type"] == "chat"
    assert latest_chat_audit["outcome"] == 1
    assert latest_chat_audit["payload"]["trace_id"]
    assert latest_chat_audit["payload"]["session_id"]
    assert latest_chat_audit["payload"]["payload"]["selected_tools"]

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
            "source": "chat",
            "event_type": "chat",
            "outcome": 1,
        },
    )
    assert extended_response.status_code == 200
    extended_body = extended_response.json()
    assert extended_body
    assert all(item["source"] == "chat" for item in extended_body)
    assert all(item["event_type"] == "chat" for item in extended_body)
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
    assert "linked_context_counts" in body


def test_audit_linked_context_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-audit-linked",
            "biz_domain": "operations",
            "message": "quota review",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    response = client.get(
        "/api/audit/linked-context",
        params={"task_id": task_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert "total_events" in body
    assert "context_counts" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    task_contexts = [
        item
        for item in body["items"]
        if item["context_type"] == "task" and item["context_id"] == task_id
    ]
    assert task_contexts
    first = task_contexts[0]
    assert first["event_count"] >= 1
    assert "actions" in first
    assert "latest_action" in first
    assert "latest_actor_id" in first
    assert "latest_created_at" in first


def test_audit_context_drilldown_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-audit-drilldown",
            "biz_domain": "operations",
            "message": "quota review",
        },
    )
    assert chat_response.status_code == 200
    task_id = chat_response.json()["task_id"]

    response = client.get(f"/api/audit/context/task/{task_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["context_type"] == "task"
    assert body["context_id"] == task_id
    assert body["event_count"] >= 1
    assert "actions" in body
    assert "events" in body
    assert body["events"]
    assert body["target"]["target_ui"] == f"/ui/tasks?task_id={task_id}"
    assert body["target"]["target_api"] == f"/api/tasks/{task_id}"
    assert any(item["task_id"] == task_id for item in body["events"])

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
    assert isinstance(body["runtime_governance"]["collaboration_view"], dict)
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
    assert "agent_count" in body["runtime_governance"]["collaboration_view"]
    assert "handoff_count" in body["runtime_governance"]["collaboration_view"]
    assert "collaboration_path" in body["runtime_governance"]["collaboration_view"]
    assert "steps" in body["runtime_governance"]["collaboration_view"]
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
    assert all(item["problem_type"] for item in body["details"])
    assert all(item["severity"] in {"low", "medium", "high"} for item in body["details"])
    assert "fallback" in body["summary"] or "工具调用" in body["summary"] or "次工具调用" in body["summary"]
    assert "governance_summary" in body
    assert body["governance_summary"]["attention_level"] in {"normal", "high"}
    assert "root_cause_signals" in body
    assert isinstance(body["root_cause_signals"], list)
    assert body["root_cause_signals"]
    assert all(
        item["severity"] in {"low", "medium", "high"}
        for item in body["root_cause_signals"]
    )
    assert isinstance(body["suggestions"], list)
    assert any(item["optimization_type"] in {"runtime", "workflow", "tool", "prompt"} for item in body["suggestions"])


def test_task_list_supports_filters(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        params={
            "status": "success",
            "biz_domain": "operations",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["page_size"] == 50
    for item in body["items"]:
        assert item["status"] == "success"
        assert item["biz_domain"] == "operations"

def test_task_list_supports_extended_filters(client: TestClient) -> None:
    response = client.get(
        "/api/tasks",
        params={
            "status": "success",
            "biz_domain": "operations",
            "selected_agent_id": "operations.quota_review",
            "risk_level": "low",
            "current_stage": "completed",
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
        assert item["status"] == "success"
        assert item["biz_domain"] == "operations"
        assert item["selected_agent_id"] == "operations.quota_review"
        assert item["risk_level"] == "low"
        assert item["current_stage"] == "completed"

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


def test_task_runtime_governance_overview_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-runtime-overview",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200

    response = client.get(
        "/api/tasks/runtime-governance/overview",
        params={"biz_domain": "operations", "limit": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert "task_count" in body
    assert "completed_task_count" in body
    assert "fallback_task_count" in body
    assert "mcp_error_task_count" in body
    assert "external_agent_error_task_count" in body
    assert "multi_agent_task_count" in body
    assert "multi_session_task_count" in body
    assert "risk_flag_counts" in body
    assert "active_agent_counts" in body
    assert "focus_tasks" in body
    assert isinstance(body["focus_tasks"], list)
    if body["focus_tasks"]:
        first = body["focus_tasks"][0]
        assert "task_id" in first
        assert "risk_score" in first
        assert "risk_flags" in first
        assert "fallback_count" in first


def test_task_realtime_ui_page(client: TestClient) -> None:
    response = client.get("/ui/tasks")
    assert response.status_code == 200
    assert 'id="agentManagerBtn"' in response.text
    assert 'id="capabilityCenterBtn"' in response.text
    assert 'id="workflowCenterBtn"' in response.text
    assert 'id="skillCenterBtn"' in response.text
    assert 'id="evaluationCenterBtn"' in response.text
    assert 'id="ticketCenterBtn"' in response.text
    assert 'id="auditCenterBtn"' in response.text
    assert 'id="taskList"' in response.text
    assert 'id="outputOverview"' in response.text
    assert 'id="gatewaySummary"' in response.text
    assert 'id="runtimeGovernanceOverview"' in response.text
    assert 'id="riskFilter"' in response.text
    assert 'id="stageFilter"' in response.text
    assert 'id="structuredToolResults"' in response.text
    assert 'id="workflowSnapshot"' in response.text
    assert 'id="skillSnapshot"' in response.text
    assert 'id="agentCollaborationView"' in response.text
    assert 'id="observations"' in response.text
    assert 'id="runtimeSessions"' in response.text
    assert 'id="runtimeGovernance"' in response.text
    assert "MCP" in response.text
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
    assert 'id="governanceIssueList"' in response.text
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
    assert "governance_status" in client.get("/api/external-agents/external.stub.agent/health").json()


def test_external_agent_governance_overview_api(client: TestClient) -> None:
    response = client.get("/api/external-agents/governance-overview")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "approval_required_count" in body
    assert "high_risk_count" in body
    assert "degraded_count" in body
    assert "blocked_count" in body
    assert "slow_count" in body
    assert "source_counts" in body
    assert "transport_counts" in body
    assert "domain_counts" in body


def test_external_agent_governance_issues_api(client: TestClient) -> None:
    response = client.get("/api/external-agents/governance-issues")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
      first = body[0]
      assert "capability_id" in first
      assert "governance_status" in first
      assert "severity" in first
      assert "reasons" in first
      assert "recommended_action" in first
      assert "target_ui" in first
      assert "target_api" in first


def test_external_agent_governance_issues_support_filters(client: TestClient) -> None:
    response = client.get(
        "/api/external-agents/governance-issues",
        params={
            "governance_status": "degraded",
            "health_status": "unknown",
            "source": "manual_remote",
            "transport": "http",
            "severity": "medium",
            "min_consecutive_failures": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for item in body:
        assert item["governance_status"] == "degraded"
        assert item["health_status"] == "unknown"
        assert item["source"] == "manual_remote"
        assert item["transport"] == "http"
        assert item["severity"] == "medium"
        assert item["target_ui"].startswith("/ui/external-agents?capability_id=")
        assert item["target_api"].startswith("/api/external-agents/")


def test_evaluations_ui_page(client: TestClient) -> None:
    response = client.get("/ui/evaluations")
    assert response.status_code == 200
    assert 'id="evaluationList"' in response.text
    assert 'id="evaluationDetail"' in response.text
    assert 'id="evaluationIdInput"' in response.text
    assert 'id="ticketPageBtn"' in response.text
    assert 'id="analyticsList"' in response.text
    assert 'id="agentFilterInput"' in response.text
    assert 'id="resultFilterInput"' in response.text
    assert 'id="suggestionList"' in response.text
    assert 'id="executionBacklogOverview"' in response.text
    assert 'id="executionBacklogList"' in response.text
    assert 'id="executionPlanOverview"' in response.text
    assert 'id="executionPlanList"' in response.text
    assert 'id="executionPlanOwnerInput"' in response.text
    assert 'id="executionPlanMaxItemsInput"' in response.text
    assert 'id="applyExecutionPlanBtn"' in response.text
    assert 'id="executionRunOverview"' in response.text
    assert 'id="executionRunList"' in response.text
    assert 'id="suggestionPriorityFilter"' in response.text
    assert 'id="loadSuggestionsBtn"' in response.text
    assert 'id="trendPanel"' in response.text
    assert 'id="focusAgentList"' in response.text
    assert 'id="governanceOverviewGrid"' in response.text
    assert 'id="governanceAgentList"' in response.text
    assert 'id="dimensionAnalyticsList"' in response.text
    assert 'id="rootCauseAnalyticsList"' in response.text
    assert "root_cause_signals" in response.text or "governance_summary" in response.text
    assert "openAudit" in response.text or "/ui/audit?" in response.text
    assert response.text.count("function renderSuggestionOverview()") == 1
    assert response.text.count("function renderAgentGovernanceOverview()") == 1
    assert response.text.count("function renderExecutionBacklogOverview()") == 1
    assert response.text.count("async function loadExecutionBacklog()") == 1
    assert response.text.count("function renderExecutionPlanOverview()") == 1
    assert response.text.count("async function loadExecutionPlan()") == 1
    assert response.text.count("async function applyExecutionPlan()") == 1
    assert response.text.count("function renderExecutionRunOverview()") == 1
    assert response.text.count("async function loadExecutionRuns()") == 1
    assert response.text.count("async function loadAgentGovernance()") == 1
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


def test_evaluation_agent_governance_api(client: TestClient) -> None:
    response = client.get("/api/evaluations/analytics/agent-governance", params={"limit": 20})
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "enabled_count" in body
    assert "high_attention_count" in body
    assert "degraded_count" in body
    assert "average_overall_score" in body
    assert "average_recent_success_rate" in body
    assert "domain_counts" in body
    assert "health_status_counts" in body
    assert "attention_level_counts" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    if body["items"]:
        first = body["items"][0]
        assert "agent_id" in first
        assert "agent_name" in first
        assert "declared_skill_count" in first
        assert "declared_mcp_count" in first
        assert "declared_workflow_count" in first
        assert "recent_task_count" in first
        assert "evaluation_count" in first
        assert "route_issue_count" in first
        assert "contract_issue_count" in first


def test_agent_governance_overview_api(client: TestClient) -> None:
    response = client.get("/api/agent-governance/overview", params={"limit": 20})
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "enabled_count" in body
    assert "high_attention_count" in body
    assert "degraded_count" in body
    assert "average_overall_score" in body
    assert "average_recent_success_rate" in body
    assert "items" in body


def test_agent_governance_issues_api_and_actions(client: TestClient) -> None:
    response = client.get("/api/agent-governance/issues", params={"limit": 50})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        first = body[0]
        assert "issue_id" in first
        assert "agent_id" in first
        assert "issue_type" in first
        assert "severity" in first
        assert "summary" in first
        assert "recommended_action" in first
        assert "target_ui" in first
        assert "target_api" in first

        filtered = client.get(
            "/api/agent-governance/issues",
            params={
                "agent_id": first["agent_id"],
                "severity": first["severity"],
                "issue_type": first["issue_type"],
            },
        )
        assert filtered.status_code == 200
        filtered_body = filtered.json()
        assert filtered_body
        assert all(item["agent_id"] == first["agent_id"] for item in filtered_body)
        assert all(item["severity"] == first["severity"] for item in filtered_body)
        assert all(item["issue_type"] == first["issue_type"] for item in filtered_body)

        action_response = client.post(
            f"/api/agent-governance/issues/{first['issue_id']}/actions",
            json={"action": "ack", "operator_id": "tester", "comment": "follow up"},
        )
        assert action_response.status_code == 200
        action_body = action_response.json()
        assert action_body["issue_id"] == first["issue_id"]
        assert action_body["action"] == "ack"
        assert action_body["status"] == "acknowledged"

        history_response = client.get(
            f"/api/agent-governance/issues/{first['issue_id']}/actions"
        )
        assert history_response.status_code == 200
        history = history_response.json()
        assert history
        assert history[-1]["issue_id"] == first["issue_id"]
        assert history[-1]["action"] == "ack"


def test_service_tickets_ui_page(client: TestClient) -> None:
    response = client.get("/ui/service-tickets")
    assert response.status_code == 200
    assert 'id="ticketOverview"' in response.text
    assert 'id="executionBacklogOverview"' in response.text
    assert 'id="executionBacklogList"' in response.text
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
    assert response.text.count("async function loadExecutionBacklog()") == 1


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
    assert "linkedContextSummary" in response.text or "linkedContextList" in response.text
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
    assert 'id="governanceIssues"' in response.text
    assert 'id="toolList"' in response.text
    assert 'id="toolDetail"' in response.text
    assert 'id="recentCalls"' in response.text
    assert "/api/mcp/tools" in response.text
    assert "Provider 风险分布" in response.text
    assert "Transport 风险分布" in response.text


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


def test_evaluation_dimension_analytics_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-eval-dimensions",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200

    response = client.get("/api/evaluations/analytics/dimensions")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    first = body[0]
    assert "dimension_code" in first
    assert "dimension_name" in first
    assert "average_score" in first
    assert "low_score_rate" in first
    assert "related_suggestion_count" in first
    assert "improvement_hint" in first


def test_evaluation_root_cause_analytics_api(client: TestClient) -> None:
    response = client.get("/api/evaluations/analytics/root-causes")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    first = body[0]
    assert "root_cause_code" in first
    assert "root_cause_name" in first
    assert "evaluation_count" in first
    assert "low_score_count" in first
    assert "average_score" in first
    assert "related_suggestion_count" in first
    assert "high_priority_suggestion_count" in first
    assert "backlog_suggestion_count" in first
    assert "attention_level" in first
    assert "impact_summary" in first
    assert "recommended_action" in first


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

    execution_backlog_response = client.get(
        "/api/evaluations/suggestions/execution-backlog",
        params={"agent_id": agent_id},
    )
    assert execution_backlog_response.status_code == 200
    execution_backlog = execution_backlog_response.json()
    assert "total" in execution_backlog
    assert "untriaged_count" in execution_backlog
    assert "ticket_pending_count" in execution_backlog
    assert "processing_count" in execution_backlog
    assert "completed_count" in execution_backlog
    assert "overdue_count" in execution_backlog
    assert "automation_ready_count" in execution_backlog
    assert "closed_loop_count" in execution_backlog
    assert "items" in execution_backlog
    assert execution_backlog["items"]
    first_backlog_item = execution_backlog["items"][0]
    assert "suggestion_id" in first_backlog_item
    assert "evaluation_id" in first_backlog_item
    assert "agent_id" in first_backlog_item
    assert "execution_stage" in first_backlog_item
    assert "attention_level" in first_backlog_item
    assert "recommended_action" in first_backlog_item

    execution_plan_response = client.get(
        "/api/evaluations/suggestions/execution-plan",
        params={"agent_id": agent_id},
    )
    assert execution_plan_response.status_code == 200
    execution_plan = execution_plan_response.json()
    assert "total_agents" in execution_plan
    assert "high_attention_agent_count" in execution_plan
    assert "automation_ready_agent_count" in execution_plan
    assert "blocked_agent_count" in execution_plan
    assert "items" in execution_plan
    assert execution_plan["items"]
    first_plan_item = execution_plan["items"][0]
    assert "agent_id" in first_plan_item
    assert "backlog_count" in first_plan_item
    assert "automation_ready_count" in first_plan_item
    assert "dependency_ticket_ids" in first_plan_item
    assert "next_step" in first_plan_item
    assert "recommended_actions" in first_plan_item

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

    suggestion_update_audit_response = client.get(
        "/api/audit",
        params={
            "action": "evaluation.suggestion.update",
            "suggestion_id": first["suggestion_id"],
        },
    )
    assert suggestion_update_audit_response.status_code == 200
    suggestion_update_audits = suggestion_update_audit_response.json()
    assert suggestion_update_audits
    suggestion_update_audit = suggestion_update_audits[0]
    assert suggestion_update_audit["source"] == "evaluation"
    assert suggestion_update_audit["event_type"] == "suggestion"
    assert suggestion_update_audit["outcome"] == 1
    assert suggestion_update_audit["payload"]["agent_id"] == agent_id
    assert suggestion_update_audit["payload"]["response_summary"] == (
        "status=in_progress, owner=agent-ops, priority=high"
    )
    assert suggestion_update_audit["payload"]["payload"]["status"] == "in_progress"
    assert suggestion_update_audit["payload"]["payload"]["owner"] == "agent-ops"
    assert suggestion_update_audit["payload"]["payload"]["priority"] == "high"

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
    ticket_create_audit = next(
        item for item in ticket_id_audit_events if item["action"] == "service_ticket.create"
    )
    ticket_update_audit = next(
        item for item in ticket_id_audit_events if item["action"] == "service_ticket.update"
    )
    assert ticket_create_audit["source"] == "evaluation"
    assert ticket_create_audit["event_type"] == "service_ticket"
    assert ticket_create_audit["payload"]["response_summary"] == (
        f"ticket created: {ticket_bound['ticket_id']}"
    )
    assert ticket_create_audit["payload"]["payload"]["ticket_status"] == "submitted"
    assert ticket_update_audit["payload"]["ticket_status"] == "resolved"
    assert ticket_update_audit["payload"]["response_summary"] == (
        "status=resolved, owner=agent-optimizer, priority=medium"
    )
    assert ticket_update_audit["payload"]["payload"]["agent_id"] == agent_id

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

    final_execution_backlog_response = client.get(
        "/api/evaluations/suggestions/execution-backlog",
        params={"agent_id": agent_id},
    )
    assert final_execution_backlog_response.status_code == 200
    final_execution_backlog = final_execution_backlog_response.json()
    assert final_execution_backlog["closed_loop_count"] >= 1
    assert any(
        item["suggestion_id"] == first["suggestion_id"] and item["execution_stage"] == "completed"
        for item in final_execution_backlog["items"]
    )


def test_execution_plan_apply_api(client: TestClient) -> None:
    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-execution-plan-apply",
            "biz_domain": "operations",
            "message": "请协助做调额审核",
        },
    )
    assert chat_response.status_code == 200
    agent_id = chat_response.json()["capability_id"]

    apply_response = client.post(
        "/api/evaluations/suggestions/execution-plan/apply",
        json={
            "requested_by": "execution-plan-bot",
            "agent_id": agent_id,
            "owner": "execution-plan-bot",
            "priority": "high",
            "max_items": 2,
        },
    )
    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["agent_id"] == agent_id
    assert applied["candidate_count"] >= 1
    assert applied["processed_count"] >= 1
    assert applied["created_ticket_count"] >= 1
    assert applied["ticket_ids"]
    assert applied["suggestion_ids"]
    assert "已处理" in applied["summary"]

    created_tickets_response = client.get(
        "/api/service-tickets",
        params={"source": "evaluation", "requested_by": "execution-plan-bot"},
    )
    assert created_tickets_response.status_code == 200
    created_tickets = created_tickets_response.json()
    created_ticket_ids = {item["ticket_id"] for item in created_tickets}
    assert set(applied["ticket_ids"]).issubset(created_ticket_ids)

    execution_plan_audit_response = client.get(
        "/api/audit",
        params={
            "action": "evaluation.execution_plan.apply",
            "actor_id": "execution-plan-bot",
        },
    )
    assert execution_plan_audit_response.status_code == 200
    execution_plan_audits = execution_plan_audit_response.json()
    assert execution_plan_audits
    assert any(
        item["action"] == "evaluation.execution_plan.apply"
        and item["payload"].get("payload", {}).get("created_ticket_count", 0) >= 1
        for item in execution_plan_audits
    )
    latest_execution_plan_audit = execution_plan_audits[0]
    assert latest_execution_plan_audit["source"] == "evaluation"
    assert latest_execution_plan_audit["event_type"] == "execution_plan"
    assert latest_execution_plan_audit["outcome"] == 1
    assert "max_items=2" in latest_execution_plan_audit["payload"]["request_summary"]
    assert latest_execution_plan_audit["payload"]["capability_id"] == agent_id
    assert latest_execution_plan_audit["payload"]["response_summary"] == applied["summary"]


def test_audit_execution_plan_runs_api(client: TestClient) -> None:
    response = client.get(
        "/api/audit/execution-plan-runs",
        params={"actor_id": "execution-plan-bot", "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "total_processed_count" in body
    assert "total_created_ticket_count" in body
    assert "items" in body
    if body["items"]:
        first = body["items"][0]
        assert "action" in first
        assert "actor_id" in first
        assert "created_at" in first
        assert "candidate_count" in first
        assert "processed_count" in first
        assert "created_ticket_count" in first
        assert "suggestion_ids" in first
        assert "ticket_ids" in first


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
