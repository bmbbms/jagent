from fastapi import FastAPI

from app.schemas import ChatRequest, ChatResponse

app = FastAPI(
    title="External Agent Stub",
    version="0.1.0",
    description="Stub external agent service for integration verification.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    summary = (
        f"External agent received task from user={request.user_id}: {request.message}"
    )
    return ChatResponse(
        domain=request.biz_domain,
        capability_id="external.stub.agent",
        capability_name="External Stub Agent",
        summary=summary,
        next_action="External stub execution completed and result returned to host platform.",
        selected_skills=["external_task_execution"],
        selected_tools=[],
        references=["stub://external-agent"],
        requires_approval=False,
        workflow=None,
        audit_tags=["external", "stub"],
    )
