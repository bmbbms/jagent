from __future__ import annotations

import argparse
import os
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_api_flow import assert_true, print_step, request_json


DEFAULT_BASE_URL = os.getenv("ACQUIRING_AI_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_EXTERNAL_BASE_URL = os.getenv(
    "ACQUIRING_AI_EXTERNAL_AGENT_BASE_URL",
    "http://127.0.0.1:8100",
)


def verify_external_agent_flow(base_url: str, external_base_url: str) -> None:
    print_step("检查主应用和外部 agent 健康状态")
    host_health = request_json(base_url, "GET", "/health")
    external_health = request_json(external_base_url, "GET", "/health")
    assert_true(host_health == {"status": "ok"}, "host health check failed")
    assert_true(external_health == {"status": "ok"}, "external agent health check failed")

    print_step("注册外部 agent")
    registered = request_json(
        base_url,
        "POST",
        "/api/external-agents/register",
        payload={
            "capability_id": "external.stub.agent",
            "capability_name": "External Stub Agent",
            "biz_domain": "merchant",
            "description": "用于验证外部 agent 接入与远程执行链路。",
            "priority": 1,
            "triggers": ["external", "stub", "remote"],
            "skills": ["external_task_execution"],
            "endpoint": external_base_url,
            "service_path": "/api/chat",
            "tags": ["verification", "external"],
            "extras": {"owner": "verification-script"},
        },
    )
    assert_true(
        registered["capability_id"] == "external.stub.agent",
        "external agent registration failed",
    )

    print_step("确认外部 agent 已可见")
    external_agents = request_json(base_url, "GET", "/api/external-agents")
    assert_true(
        any(item["capability_id"] == "external.stub.agent" for item in external_agents),
        "external agent not listed",
    )
    capabilities = request_json(base_url, "GET", "/api/capabilities")
    assert_true(
        any(item["capability_id"] == "external.stub.agent" for item in capabilities),
        "external agent not exposed in capabilities",
    )

    print_step("发起定向到外部 agent 的任务")
    response = request_json(
        base_url,
        "POST",
        "/api/chat",
        payload={
            "user_id": "verify-external-agent",
            "biz_domain": "merchant",
            "message": "请把这个 external task 交给远程 agent 执行",
            "metadata": {"requested_agent_id": "external.stub.agent"},
        },
    )
    task_id = str(response["task_id"])
    assert_true(
        response["capability_id"] == "external.stub.agent",
        "chat did not route to external stub agent",
    )
    assert_true(
        response["routing_trace"]["selected_capability_id"] == "external.stub.agent",
        "routing trace did not record external agent selection",
    )

    detail = request_json(base_url, "GET", f"/api/tasks/{task_id}")
    assert_true(
        detail["selected_agent_id"] == "external.stub.agent",
        "task detail selected_agent_id mismatch",
    )
    assert_true(
        "External agent received task" in detail["final_output_summary"],
        "task output does not contain external agent result",
    )

    print_step(f"外部 agent 验证通过: task_id={task_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify external agent integration flow.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Host API base URL, default: %(default)s",
    )
    parser.add_argument(
        "--external-base-url",
        default=DEFAULT_EXTERNAL_BASE_URL,
        help="External agent base URL, default: %(default)s",
    )
    args = parser.parse_args()

    try:
        verify_external_agent_flow(
            base_url=args.base_url,
            external_base_url=args.external_base_url,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[verify] failed: {exc}", file=sys.stderr)
        return 1

    print_step("外部 agent 接入与执行链路验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
