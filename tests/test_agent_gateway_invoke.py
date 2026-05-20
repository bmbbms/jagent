from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fastapi.testclient import TestClient

from app.dependencies import get_agent_profile_sync_service
from app.main import app


class _FakeNacosClient:
    def __init__(self, cards: list[dict]) -> None:
        self._cards = cards

    def list_agent_cards(self, *, page_size: int = 100):  # noqa: ANN001
        return self._cards


class _GatewayTargetStubHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        body = {
            "domain": payload["biz_domain"],
            "capability_id": "nacos.merchant.gateway.target",
            "capability_name": "Gateway Target Agent",
            "summary": f"gateway target handled: {payload['message']}",
            "next_action": "review completed",
            "selected_skills": ["regulation_query"],
            "selected_tools": [],
            "references": ["stub://gateway-target"],
            "requires_approval": False,
            "workflow": None,
            "audit_tags": ["gateway_target"],
            "approval_id": None,
            "task_id": None,
            "evaluation_id": None,
            "routing_trace": None,
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def test_agent_gateway_invoke_records_route_and_declared_capabilities() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GatewayTargetStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    service = get_agent_profile_sync_service()
    original_client = service._client
    service._client = _FakeNacosClient(
        [
            {
                "name": "gateway-target-agent",
                "description": "handles regulation and compliance questions",
                "version": "1.0.0",
                "url": f"http://127.0.0.1:{server.server_port}/api/chat",
                "skills": [
                    {
                        "id": "regulation_query",
                        "name": "Regulation Query",
                        "description": "query regulation rules",
                    }
                ],
                "metadata": {
                    "capability_id": "nacos.merchant.gateway.target",
                    "biz_domain": "merchant",
                    "transport": "http",
                    "tags": ["regulation", "gateway"],
                    "mcps": [
                        {
                            "id": "merchant-risk-mcp",
                            "name": "Merchant Risk MCP",
                            "description": "risk lookup",
                        }
                    ],
                    "workflows": [
                        {
                            "id": "gateway-review-workflow",
                            "name": "Gateway Review Workflow",
                            "description": "review workflow",
                        }
                    ],
                },
            }
        ]
    )

    try:
        with TestClient(app) as client:
            sync_response = client.post("/api/agent-profiles/sync")
            assert sync_response.status_code == 200
            assert sync_response.json()["upserted_count"] >= 1

            invoke_response = client.post(
                "/api/agent-gateway/invoke",
                json={
                    "user_id": "u-agent-gateway",
                    "biz_domain": "merchant",
                    "message": "please run regulation review",
                    "requested_agent_id": "nacos.merchant.gateway.target",
                    "roles": ["risk_admin"],
                    "source": "api",
                    "metadata": {"ticket_id": "GW-001"},
                },
            )
            assert invoke_response.status_code == 200
            body = invoke_response.json()
            assert body["selected_agent_id"] == "nacos.merchant.gateway.target"
            assert body["selected_agent_name"] == "gateway-target-agent"
            assert "regulation_query" in body["matched_skill_ids"]
            assert body["declared_skills"][0]["skill_id"] == "regulation_query"
            assert body["declared_mcps"][0]["mcp_id"] == "merchant-risk-mcp"
            assert body["declared_workflows"][0]["workflow_id"] == "gateway-review-workflow"
            assert "gateway target handled" in body["summary"]
            assert "agent_gateway" in body["audit_tags"]
            assert body["routing_trace"]["selected_capability_id"] == "nacos.merchant.gateway.target"
            assert body["task_id"]

            task_id = body["task_id"]
            task_detail_response = client.get(f"/api/tasks/{task_id}")
            assert task_detail_response.status_code == 200
            task_detail = task_detail_response.json()
            assert task_detail["gateway_summary"]["selected_agent_id"] == "nacos.merchant.gateway.target"
            assert task_detail["gateway_summary"]["policy_decision"] == "allow"
            assert task_detail["gateway_summary"]["declared_skills"][0]["skill_id"] == "regulation_query"
            assert task_detail["gateway_summary"]["declared_mcps"][0]["mcp_id"] == "merchant-risk-mcp"
            assert task_detail["gateway_summary"]["declared_workflows"][0]["workflow_id"] == "gateway-review-workflow"
            assert task_detail["evaluation"] is not None
            detail_dimension_codes = {item["dimension_code"] for item in task_detail["evaluation"]["details"]}
            assert "gateway_routing" in detail_dimension_codes
            assert "gateway_contract" in detail_dimension_codes
            event_types = [item["event_type"] for item in task_detail["events"]]
            assert "gateway_policy_checked" in event_types
            assert "agent_selected" in event_types
            assert "gateway_declared_contract_loaded" in event_types
            assert "external_agent_call_started" in event_types
            assert "external_agent_call_finished" in event_types
            assert "final_response" in event_types

            declared_event = next(
                item
                for item in task_detail["events"]
                if item["event_type"] == "gateway_declared_contract_loaded"
            )
            assert declared_event["event_payload"]["declared_skills"][0]["skill_id"] == "regulation_query"
            assert declared_event["event_payload"]["declared_mcps"][0]["mcp_id"] == "merchant-risk-mcp"

            selected_event = next(
                item for item in task_detail["events"] if item["event_type"] == "agent_selected"
            )
            assert selected_event["event_payload"]["policy_decision"] == "allow"
            assert selected_event["event_payload"]["capability_id"] == "nacos.merchant.gateway.target"

            audit_response = client.get(
                "/api/audit",
                params={"action": "agent_gateway.invoke", "task_id": task_id},
            )
            assert audit_response.status_code == 200
            audit_items = audit_response.json()
            assert audit_items
            latest = audit_items[0]
            assert latest["source"] == "agent_gateway"
            assert latest["event_type"] == "gateway_invoke"
            assert latest["payload"]["capability_id"] == "nacos.merchant.gateway.target"
            assert latest["payload"]["payload"]["selected_agent_id"] == "nacos.merchant.gateway.target"

            evaluation_response = client.get(f"/api/tasks/{task_id}/evaluation")
            assert evaluation_response.status_code == 200
            evaluation = evaluation_response.json()
            assert evaluation["evaluation_id"]
            evaluation_codes = {item["dimension_code"] for item in evaluation["details"]}
            assert "gateway_routing" in evaluation_codes
            assert "gateway_contract" in evaluation_codes
    finally:
        service._client = original_client
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
