from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_BASE_URL = os.getenv("ACQUIRING_AI_BASE_URL", "http://127.0.0.1:8000")


@dataclass
class SseMessage:
    event: str
    data: dict[str, Any]
    event_id: str | None = None


def build_url(base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        filtered = {key: value for key, value in query.items() if value is not None}
        if filtered:
            url = f"{url}?{parse.urlencode(filtered)}"
    return url


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any] | list[Any]:
    url = build_url(base_url, path, query=query)
    body: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method.upper()} {path} failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method.upper()} {path} failed: {exc}") from exc


def iter_sse(
    base_url: str,
    path: str,
    query: dict[str, Any] | None = None,
    timeout: float = 40.0,
) -> list[SseMessage]:
    url = build_url(base_url, path, query=query)
    req = request.Request(url, method="GET", headers={"Accept": "text/event-stream"})
    messages: list[SseMessage] = []

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            current_event = "message"
            current_data_lines: list[str] = []
            current_id: str | None = None

            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if not line:
                    if current_data_lines:
                        data_text = "\n".join(current_data_lines)
                        try:
                            parsed_data = json.loads(data_text)
                        except json.JSONDecodeError:
                            parsed_data = {"raw": data_text}
                        messages.append(
                            SseMessage(
                                event=current_event,
                                data=parsed_data,
                                event_id=current_id,
                            )
                        )
                        current_event = "message"
                        current_data_lines = []
                        current_id = None
                    continue

                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    current_data_lines.append(line.split(":", 1)[1].strip())
                elif line.startswith("id:"):
                    current_id = line.split(":", 1)[1].strip()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"GET {path} failed: {exc}") from exc

    return messages


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def print_step(message: str) -> None:
    print(f"[verify] {message}")


def verify_health(base_url: str) -> None:
    print_step("检查 /health")
    body = request_json(base_url, "GET", "/health")
    assert_true(body == {"status": "ok"}, "health check failed")


def verify_merchant_flow(base_url: str) -> None:
    print_step("验证 merchant 对话链路")
    chat_body = request_json(
        base_url,
        "POST",
        "/api/chat",
        payload={
            "user_id": "verify-merchant",
            "biz_domain": "merchant",
            "message": "请帮我解答商户规则问题",
        },
    )
    task_id = str(chat_body["task_id"])
    evaluation_id = str(chat_body["evaluation_id"])

    assert_true(chat_body["capability_id"] == "merchant.qa", "unexpected merchant capability")
    assert_true(chat_body["approval_id"] is None, "merchant flow should not require approval")
    assert_true("Runtime=agentscope" in chat_body["routing_trace"]["reason"], "runtime trace mismatch")

    detail = request_json(base_url, "GET", f"/api/tasks/{task_id}")
    assert_true(detail["status"] == "success", "merchant task should be success")
    assert_true(len(detail["artifacts"]) >= 1, "merchant task should generate artifact")

    event_types = [event["event_type"] for event in detail["events"]]
    for required in [
        "task_created",
        "agent_selected",
        "agent_started",
        "runtime_session_started",
        "skill_bundle_loaded",
        "tool_inventory_prepared",
        "planner_started",
        "execution_plan_created",
        "planner_completed",
        "executor_started",
        "thought_generated",
        "executor_completed",
        "final_response",
        "artifact_generated",
    ]:
        assert_true(required in event_types, f"merchant task missing event: {required}")

    sse_messages = iter_sse(
        base_url,
        f"/api/tasks/{task_id}/events/stream",
        query={"last_event_seq": 0, "poll_interval": 0.2, "max_idle_rounds": 3},
    )
    sse_event_types = [message.event for message in sse_messages]
    assert_true("task_created" in sse_event_types, "merchant sse missing task_created")
    assert_true("task_completed" in sse_event_types, "merchant sse missing task_completed")

    evaluation = request_json(base_url, "GET", f"/api/evaluations/{evaluation_id}")
    assert_true(evaluation["task_id"] == task_id, "merchant evaluation task_id mismatch")
    assert_true(len(evaluation["details"]) >= 1, "merchant evaluation details missing")
    assert_true(len(evaluation["suggestions"]) >= 1, "merchant evaluation suggestions missing")

    print_step(f"merchant 链路通过: task_id={task_id}, evaluation_id={evaluation_id}")


def verify_operations_flow(base_url: str) -> None:
    print_step("验证 operations 审批链路")
    chat_body = request_json(
        base_url,
        "POST",
        "/api/chat",
        payload={
            "user_id": "verify-operations",
            "biz_domain": "operations",
            "message": "quota review",
        },
    )
    task_id = str(chat_body["task_id"])
    approval_id = str(chat_body["approval_id"])
    evaluation_id = str(chat_body["evaluation_id"])

    assert_true(chat_body["capability_id"] == "operations.quota_review", "unexpected operations capability")
    assert_true(chat_body["requires_approval"] is True, "operations flow should require approval")
    assert_true(bool(approval_id), "operations approval_id missing")

    before_detail = request_json(base_url, "GET", f"/api/tasks/{task_id}")
    assert_true(
        before_detail["status"] == "waiting_approval",
        "operations task should enter waiting_approval before decision",
    )

    decision_body = request_json(
        base_url,
        "POST",
        f"/api/approvals/{approval_id}/decision",
        payload={
            "reviewer_id": "verify-reviewer",
            "decision": "approve",
            "comment": "verification approved",
        },
    )
    assert_true(decision_body["status"] == "approved", "approval decision should be approved")

    final_detail = wait_for_task_status(
        base_url=base_url,
        task_id=task_id,
        expected_status="success",
        timeout_seconds=15.0,
    )

    event_types = [event["event_type"] for event in final_detail["events"]]
    for required in [
        "runtime_session_started",
        "planner_started",
        "execution_plan_created",
        "planner_completed",
        "executor_started",
        "executor_completed",
        "approval_requested",
        "approval_finished",
        "final_response",
        "artifact_generated",
    ]:
        assert_true(required in event_types, f"operations task missing event: {required}")

    sse_messages = iter_sse(
        base_url,
        f"/api/tasks/{task_id}/events/stream",
        query={"last_event_seq": 0, "poll_interval": 0.2, "max_idle_rounds": 3},
    )
    sse_event_types = [message.event for message in sse_messages]
    assert_true("approval_requested" in sse_event_types, "operations sse missing approval_requested")
    assert_true("approval_finished" in sse_event_types, "operations sse missing approval_finished")
    assert_true("task_completed" in sse_event_types, "operations sse missing task_completed")

    evaluation = request_json(base_url, "GET", f"/api/evaluations/{evaluation_id}")
    assert_true(evaluation["task_id"] == task_id, "operations evaluation task_id mismatch")

    print_step(
        f"operations 链路通过: task_id={task_id}, approval_id={approval_id}, evaluation_id={evaluation_id}"
    )


def wait_for_task_status(
    *,
    base_url: str,
    task_id: str,
    expected_status: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_detail: dict[str, Any] | None = None

    while time.time() < deadline:
        detail = request_json(base_url, "GET", f"/api/tasks/{task_id}")
        last_detail = detail
        if detail["status"] == expected_status:
            return detail
        time.sleep(0.5)

    raise AssertionError(
        f"task {task_id} did not reach status={expected_status}, "
        f"last_status={last_detail['status'] if last_detail else 'unknown'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify jagent API end-to-end flows.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API base URL, default: %(default)s",
    )
    args = parser.parse_args()

    try:
        verify_health(args.base_url)
        verify_merchant_flow(args.base_url)
        verify_operations_flow(args.base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"[verify] failed: {exc}", file=sys.stderr)
        return 1

    print_step("全部 API 验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
