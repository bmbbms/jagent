from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/tasks")
def task_realtime_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "task-realtime.html"
    return FileResponse(page_path)


@router.get("/chat")
def chat_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "chat-console.html"
    return FileResponse(page_path)


@router.get("/external-agents")
def external_agent_page() -> FileResponse:
    page_path = (
        Path(__file__).resolve().parents[2] / "static" / "external-agent-manager.html"
    )
    return FileResponse(page_path)


@router.get("/evaluations")
def evaluations_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "evaluations-dashboard.html"
    return FileResponse(page_path)


@router.get("/agent-profiles")
def agent_profiles_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "agent-profile-center.html"
    return FileResponse(page_path)


@router.get("/audit")
def audit_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "audit-dashboard.html"
    return FileResponse(page_path)


@router.get("/service-tickets")
def service_tickets_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "service-ticket-dashboard.html"
    return FileResponse(page_path)


@router.get("/workflows")
def workflows_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "workflows-dashboard.html"
    return FileResponse(page_path)


@router.get("/skills")
def skills_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "skills-dashboard.html"
    return FileResponse(page_path)


@router.get("/capabilities")
def capabilities_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "capabilities-dashboard.html"
    return FileResponse(page_path)


@router.get("/mcp")
def mcp_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "mcp-dashboard.html"
    return FileResponse(page_path)
