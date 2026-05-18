from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    ApprovalTaskModel,
    DataAccessLogModel,
    DirectSalesMetricDailyModel,
    ReportExportJobModel,
    ServiceTicketModel,
    ToolCallLogModel,
)
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.services.internal_tool_registry import (
    FallbackInternalToolAdapter,
    InternalToolRegistry,
    build_default_internal_tool_registry,
)
from app.services.internal_tool_provider import LocalDbInternalToolProvider
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.services.tool_execution_service import ToolExecutionService


def _build_test_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_tool_execution_service_emits_internal_tool_events() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )
    captured_events: list[dict] = []

    def emit_event(**payload):
        captured_events.append(payload)
        return {"event_id": f"evt_{len(captured_events)}", "event_seq": len(captured_events)}

    result = service.execute_tool(
        tool_id="merchant_profile_query",
        request_context={
            "task_id": "task_tool_test",
            "contact_id": "ct_tool_test",
            "merchant_id": "M123456",
            "request_message": "查询商户档案",
        },
        emit_event=emit_event,
        agent_id="merchant.qa",
    )

    assert result.tool_id == "merchant_profile_query"
    assert result.status == "success"
    assert result.payload["result"]["merchant_id"] == "M123456"
    assert [item["event_type"] for item in captured_events] == [
        "tool_call_started",
        "tool_call_finished",
    ]
    assert all(item["task_id"] == "task_tool_test" for item in captured_events)


def test_tool_execution_service_persists_tool_and_data_access_logs() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="merchant_transaction_summary",
        request_context={"task_id": "task_txn", "merchant_id": "M654321"},
        agent_id="operations.quota_review",
    )

    assert result.status == "success"

    with session_factory() as session:
        tool_logs = session.query(ToolCallLogModel).all()
        data_logs = session.query(DataAccessLogModel).all()

    assert len(tool_logs) == 1
    assert tool_logs[0].task_id == "task_txn"
    assert tool_logs[0].tool_id == "merchant_transaction_summary"
    assert tool_logs[0].status == "success"

    assert len(data_logs) == 1
    assert data_logs[0].task_id == "task_txn"
    assert data_logs[0].data_object == "t_merchant_transaction_daily"
    assert data_logs[0].access_type == "read"


def test_tool_execution_service_supports_custom_registry_override() -> None:
    session_factory = _build_test_session_factory()
    registry = InternalToolRegistry(
        fallback_adapter=FallbackInternalToolAdapter(),
    )
    service = ToolExecutionService(
        internal_tool_registry=registry,
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="ticket_submit",
        request_context={"task_id": "task_custom"},
    )

    assert result.status == "success"
    assert result.payload["result"]["accepted"] is True


def test_ticket_submit_persists_service_ticket_and_write_log() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="ticket_submit",
        request_context={
            "task_id": "task_ticket",
            "merchant_id": "M100001",
            "user_id": "u_tool",
            "request_message": "商户昨日结算失败，需要排查",
            "kwargs": {
                "category": "settlement",
                "priority": "high",
                "title": "结算异常排查",
            },
        },
        agent_id="operations.agent",
    )

    assert result.status == "success"
    ticket_id = result.payload["result"]["ticket_id"]

    with session_factory() as session:
        ticket = session.get(ServiceTicketModel, ticket_id)
        data_logs = (
            session.query(DataAccessLogModel)
            .filter(DataAccessLogModel.task_id == "task_ticket")
            .all()
        )

    assert ticket is not None
    assert ticket.category == "settlement"
    assert ticket.priority == "high"
    assert ticket.requested_by == "u_tool"
    assert len(data_logs) == 1
    assert data_logs[0].data_object == "t_service_ticket"
    assert data_logs[0].access_type == "write"


def test_quota_approval_submit_persists_approval_task() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="quota_approval_submit",
        request_context={
            "task_id": "task_approval",
            "contact_id": "ct_approval",
            "merchant_id": "M200001",
            "user_id": "u_reviewer",
            "request_message": "申请将商户单笔额度提升到 20 万",
            "kwargs": {
                "apply_amount": 2000000,
                "reason": "优质存量商户大额交易需求",
            },
        },
        agent_id="operations.quota_review",
    )

    assert result.status == "success"
    approval_id = result.payload["result"]["approval_id"]

    with session_factory() as session:
        approval = session.get(ApprovalTaskModel, approval_id)

    assert approval is not None
    assert approval.approval_type == "quota_adjustment"
    assert approval.status == "pending"
    assert approval.requested_by == "u_reviewer"
    assert approval.payload["apply_amount"] == 2000000


def test_direct_sales_metrics_query_reads_metric_table() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="direct_sales_metrics_query",
        request_context={
            "task_id": "task_metrics",
            "kwargs": {"metrics_date": "2026-05-18", "region_code": "east"},
        },
        agent_id="data.metrics",
    )

    assert result.status == "success"
    assert result.payload["result"]["region_code"] == "east"
    assert result.payload["result"]["sales_amount_yuan"] == 892000.0

    with session_factory() as session:
        metric = (
            session.query(DirectSalesMetricDailyModel)
            .filter(DirectSalesMetricDailyModel.stat_date == "2026-05-18")
            .filter(DirectSalesMetricDailyModel.region_code == "east")
            .one_or_none()
        )

    assert metric is not None
    assert metric.sales_amount == 89200000


def test_compliance_report_export_persists_export_job() -> None:
    session_factory = _build_test_session_factory()
    service = ToolExecutionService(
        internal_tool_registry=build_default_internal_tool_registry(
            LocalDbInternalToolProvider(session_factory)
        ),
        log_service=ToolExecutionLogService(
            session_factory=session_factory,
            repository=ToolExecutionRepository(),
        ),
    )

    result = service.execute_tool(
        tool_id="compliance_report_export",
        request_context={
            "task_id": "task_report",
            "user_id": "u_data",
            "request_message": "导出昨日合规巡检报表",
            "kwargs": {"format": "csv", "report_type": "compliance_daily"},
        },
        agent_id="data.compliance",
    )

    assert result.status == "success"
    report_id = result.payload["result"]["report_id"]

    with session_factory() as session:
        report = session.get(ReportExportJobModel, report_id)
        data_log = (
            session.query(DataAccessLogModel)
            .filter(DataAccessLogModel.task_id == "task_report")
            .one()
        )

    assert report is not None
    assert report.format == "csv"
    assert report.report_type == "compliance_daily"
    assert report.requested_by == "u_data"
    assert report.output_uri == f"/exports/{report_id}.csv"
    assert data_log.data_object == "t_report_export_job"
    assert data_log.access_type == "write"
