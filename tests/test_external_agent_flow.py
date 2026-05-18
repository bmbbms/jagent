from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_manual_remote_registry
from app.main import app


class _ExternalAgentStubHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        self._write_json({"status": "ok"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        self._write_json(
            {
                "domain": payload["biz_domain"],
                "capability_id": "external.stub.agent",
                "capability_name": "External Stub Agent",
                "summary": f"External agent processed: {payload['message']}",
                "next_action": "Remote execution finished.",
                "selected_skills": ["external_task_execution"],
                "selected_tools": [],
                "references": ["stub://external-agent"],
                "requires_approval": False,
                "workflow": None,
                "audit_tags": ["external", "stub"],
                "approval_id": None,
                "task_id": None,
                "evaluation_id": None,
                "routing_trace": None,
            }
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _A2AExternalAgentStubHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/.well-known/agent-card.json", "/.well-known/agent.json"}:
            self.send_response(404)
            self.end_headers()
            return
        self._write_json(
            {
                "name": "Payment Regulation Agent",
                "description": "A2A discovery test agent",
                "protocolVersion": "0.3.0",
                "preferredTransport": "JSONRPC",
                "version": "1.0.0",
                "skills": [
                    {"id": "dialog", "name": "Dialog"},
                    {"id": "regulation_query", "name": "Regulation Query"},
                ],
                "url": f"http://127.0.0.1:{self.server.server_port}/a2a",
            }
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/a2a":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        user_text = payload["params"]["message"]["parts"][0]["text"]

        events = [
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "result": {
                    "kind": "status-update",
                    "taskId": "stub-task-id",
                    "contextId": "stub-context-id",
                    "final": False,
                    "status": {"state": "working"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "result": {
                    "kind": "message",
                    "messageId": "stub-message-id",
                    "role": "agent",
                    "parts": [
                        {
                            "kind": "text",
                            "text": f"A2A external agent processed: {user_text}",
                        }
                    ],
                },
            },
        ]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()
        for event in events:
            chunk = f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(chunk)
            self.wfile.flush()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def external_agent_server() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ExternalAgentStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture(scope="module")
def a2a_external_agent_server() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _A2AExternalAgentStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture(autouse=True)
def clear_manual_registry() -> None:
    registry = get_manual_remote_registry()
    registry.clear()
    yield
    registry.clear()


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_register_and_route_external_agent(
    client: TestClient,
    external_agent_server: str,
) -> None:
    register_response = client.post(
        "/api/external-agents/register",
        json={
            "capability_id": "external.stub.agent",
            "capability_name": "External Stub Agent",
            "biz_domain": "merchant",
            "description": "External agent integration verification",
            "priority": 1,
            "triggers": ["external", "remote"],
            "skills": ["external_task_execution"],
            "endpoint": external_agent_server,
            "service_path": "/api/chat",
            "tags": ["test"],
        },
    )
    assert register_response.status_code == 200
    assert register_response.json()["capability_id"] == "external.stub.agent"

    external_agents_response = client.get("/api/external-agents")
    assert external_agents_response.status_code == 200
    external_agents = external_agents_response.json()
    assert any(item["capability_id"] == "external.stub.agent" for item in external_agents)

    capabilities_response = client.get("/api/capabilities")
    assert capabilities_response.status_code == 200
    capabilities = capabilities_response.json()
    assert any(item["capability_id"] == "external.stub.agent" for item in capabilities)

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-external-agent",
            "biz_domain": "merchant",
            "message": "请执行 external remote task",
            "metadata": {"requested_agent_id": "external.stub.agent"},
        },
    )
    assert chat_response.status_code == 200
    chat_body = chat_response.json()
    assert chat_body["capability_id"] == "external.stub.agent"
    assert chat_body["routing_trace"]["selected_capability_id"] == "external.stub.agent"
    assert chat_body["task_id"] is not None

    task_detail_response = client.get(f"/api/tasks/{chat_body['task_id']}")
    assert task_detail_response.status_code == 200
    task_detail = task_detail_response.json()
    assert task_detail["selected_agent_id"] == "external.stub.agent"
    assert "External agent processed" in task_detail["final_output_summary"]


def test_register_and_route_a2a_external_agent(
    client: TestClient,
    a2a_external_agent_server: str,
) -> None:
    register_response = client.post(
        "/api/external-agents/register",
        json={
            "capability_id": "external.a2a.agent",
            "capability_name": "External A2A Agent",
            "biz_domain": "merchant",
            "description": "External A2A integration verification",
            "priority": 1,
            "triggers": ["功能", "合规"],
            "skills": ["external_task_execution"],
            "transport": "a2a",
            "endpoint": a2a_external_agent_server,
            "service_path": "/a2a",
            "tags": ["test", "a2a"],
        },
    )
    assert register_response.status_code == 200
    assert register_response.json()["capability_id"] == "external.a2a.agent"

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-a2a-external-agent",
            "biz_domain": "merchant",
            "message": "你支持的功能",
            "metadata": {"requested_agent_id": "external.a2a.agent"},
        },
    )
    assert chat_response.status_code == 200
    chat_body = chat_response.json()
    assert chat_body["capability_id"] == "external.a2a.agent"
    assert "transport:a2a" in chat_body["audit_tags"]
    assert chat_body["routing_trace"]["selected_capability_id"] == "external.a2a.agent"

    task_detail_response = client.get(f"/api/tasks/{chat_body['task_id']}")
    assert task_detail_response.status_code == 200
    task_detail = task_detail_response.json()
    assert task_detail["selected_agent_id"] == "external.a2a.agent"
    assert "A2A external agent processed" in task_detail["final_output_summary"]


def test_discover_and_add_generic_a2a_agent(
    client: TestClient,
    a2a_external_agent_server: str,
) -> None:
    discover_response = client.post(
        "/api/external-agents/discover",
        json={
            "agent_url": a2a_external_agent_server,
            "biz_domain": "merchant",
            "priority": 5,
            "tags": ["generic-add"],
        },
    )
    assert discover_response.status_code == 200
    discovered = discover_response.json()
    assert discovered["transport"] == "a2a"
    assert discovered["service_path"] == "/a2a"
    assert discovered["capability_name"] == "Payment Regulation Agent"
    assert discovered["skills"] == ["dialog", "regulation_query"]
    assert discovered["source"] == "generic_add"

    add_response = client.post(
        "/api/external-agents/add",
        json={
            "agent_url": a2a_external_agent_server,
            "biz_domain": "merchant",
            "priority": 5,
            "tags": ["generic-add"],
            "triggers": ["法规", "合规"],
        },
    )
    assert add_response.status_code == 200
    added = add_response.json()
    assert added["transport"] == "a2a"
    assert added["source"] == "generic_add"
    assert added["capability_id"].startswith("external.a2a.")

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "u-generic-a2a-agent",
            "biz_domain": "merchant",
            "message": "你支持的功能",
            "metadata": {"requested_agent_id": added["capability_id"]},
        },
    )
    assert chat_response.status_code == 200
    chat_body = chat_response.json()
    assert chat_body["capability_id"] == added["capability_id"]
    assert "transport:a2a" in chat_body["audit_tags"]
