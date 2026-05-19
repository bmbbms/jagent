from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/tasks")
def task_realtime_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "task-realtime.html"
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


@router.get("/approvals")
def approvals_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "approvals-dashboard.html"
    return FileResponse(page_path)


@router.get("/audit")
def audit_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "audit-dashboard.html"
    return FileResponse(page_path)


@router.get("/workflows")
def workflows_page() -> FileResponse:
    page_path = Path(__file__).resolve().parents[2] / "static" / "workflows-dashboard.html"
    return FileResponse(page_path)
